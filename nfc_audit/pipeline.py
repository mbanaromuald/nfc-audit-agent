"""Orchestrateur central : enchaîne les quatre agents et produit le jeu de résultats."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pandas as pd

from .anonymizer import Anonymizer
from .config import FRAMEWORKS, LEVELS
from .knowledge import NORMS_BY_ID
from .llm import LLMAuthError, build_llm, invoke_text, parse_json
from .risk import evaluate, level_from_score


def _max_level(a: str, b: str) -> str:
    return a if LEVELS.index(a) >= LEVELS.index(b) else b


def _event_prompt(ev: dict, retrieved: list[dict], rules: list[dict]) -> str:
    norms = "\n".join(f"- {n['source']} – {n['article']} : {n['content']}" for n in retrieved)
    findings = "\n".join(f"- {r['title']} : {r['detail']}" for r in rules) or "- Aucun écart détecté par les règles déterministes."
    return f"""Tu es l'Agent Expert en Audit et Conformité SI de NFC Bank (banque camerounaise régulée par la COBAC).
Évalue l'événement ci-dessous. Les identifiants sont pseudonymisés : ne tente pas de les deviner.

ÉVÉNEMENT :
- Horodatage : {ev['timestamp']}
- Système : {ev['source_sys']} (Event ID {ev['event_id']})
- Action : {ev['action']}
- Acteur : {ev['actor']}
- Cible : {ev['user_target']}
- Ressource : {ev['resource']}
- Ticket ITSM : {ev['ticket_ref']}
- Statut : {ev['status']}

ÉCARTS DÉJÀ DÉTECTÉS PAR LE MOTEUR DE RÈGLES :
{findings}

RÉFÉRENTIELS APPLICABLES (issus de la recherche vectorielle) :
{norms}

Consignes :
1. Confirme ou nuance la non-conformité (absence de ticket, violation d'accès, séparation des fonctions, corrélation).
2. Attribue un niveau parmi CRITIQUE, ELEVE, MOYEN, FAIBLE.
3. Cite uniquement les exigences des référentiels ci-dessus réellement enfreintes.
4. Rédige en français, sans inventer de faits absents de l'événement.

Réponds uniquement avec un objet JSON, sans texte autour :
{{"non_conformite": "Oui|Non", "niveau_risque": "CRITIQUE|ELEVE|MOYEN|FAIBLE",
"normes_violees": ["source – article"], "justification": "2 phrases maximum",
"recommandation": "action corrective immédiate en 1 à 2 phrases"}}"""


def _framework_scores(results: list[dict]) -> dict[str, float]:
    total = max(len(results), 1)
    scores = {}
    for key, _label in FRAMEWORKS:
        violated = sum(1 for r in results if any(n["framework"] == key for n in r["norms"]))
        scores[key] = round(100 * (total - violated) / total, 1)
    return scores


def _fallback_summary(stats: dict) -> str:
    c = stats["by_level"]
    return (
        f"L'analyse de {stats['total']} événements fait ressortir {stats['nonconform']} non-conformités, dont "
        f"{c['CRITIQUE']} critiques et {c['ELEVE']} élevées. Le taux de conformité global s'établit à "
        f"{stats['compliance_rate']} %. Les écarts dominants concernent l'absence de ticket de changement "
        "associé à des opérations privilégiées ou en production, ainsi que des comportements d'authentification "
        "anormaux. Il est recommandé de traiter en priorité les écarts critiques (révocation des droits non "
        "autorisés, régularisation des RFC) puis de renforcer les contrôles préventifs dans l'ITSM."
    )


def run_audit(
    df: pd.DataFrame,
    retriever,
    api_key: str | None = None,
    model: str = "llama-3.3-70b-versatile",
    use_llm: bool = True,
    approved_tickets: set[str] | None = None,
    max_llm_events: int = 25,
    progress=None,
) -> dict:
    t0 = time.perf_counter()
    notify = progress or (lambda frac, msg: None)
    warnings: list[str] = []
    anon = Anonymizer()
    df = df.reset_index(drop=True)

    # 1) Agent Ingestion : données déjà normalisées ; pseudonymisation pour le LLM
    notify(0.05, "Agent Ingestion : normalisation et pseudonymisation des journaux…")
    events = df.to_dict("records")
    for e in events:
        e["event_id"] = "" if pd.isna(e["event_id"]) else int(e["event_id"])
    anon_events = []
    for e in events:
        a = dict(e)
        a["actor"] = anon.token(e["actor"], "USER")
        a["user_target"] = anon.token(e["user_target"], "USER")
        a["ip_address"] = anon.token(e["ip_address"], "IP") if e["ip_address"] else ""
        a["action"] = anon.text(e["action"])
        a["resource"] = anon.text(e["resource"])
        anon_events.append(a)

    # 2) Agent Évaluation des risques : règles + corrélation
    notify(0.2, "Agent Évaluation : application des règles et corrélation des événements…")
    rule_hits = evaluate(df, approved_tickets)

    # 3) Agent RAG : recherche des références applicables
    notify(0.35, "Agent RAG : recherche vectorielle des référentiels applicables…")
    results: list[dict] = []
    for i, e in enumerate(events):
        rules = rule_hits[i]
        query = f"{e['source_sys']} {e['action']} " + " ".join(r["title"] for r in rules)
        retrieved = retriever.search(query, k=3)
        score = max((r["impact"] * r["probability"] for r in rules), default=1)
        top = max(rules, key=lambda r: r["impact"] * r["probability"]) if rules else None
        norm_ids = []
        for r in rules:
            for nid in r["norm_ids"]:
                if nid not in norm_ids:
                    norm_ids.append(nid)
        results.append({
            "idx": i + 1,
            "log": e,
            "rules": rules,
            "impact": top["impact"] if top else 1,
            "probability": top["probability"] if top else 1,
            "score": score,
            "rule_level": level_from_score(score) if rules else "FAIBLE",
            "level": level_from_score(score) if rules else "FAIBLE",
            "norms": [NORMS_BY_ID[n] for n in norm_ids],
            "retrieved": retrieved,
            "non_conforme": bool(rules),
            "justification": " ".join(r["detail"] for r in rules) if rules else
                             "Opération rattachée à un ticket valide : aucun écart détecté.",
            "recommendation": top["recommendation"] if top else "Aucune action requise.",
            "llm": None,
            "mode": "règles",
        })

    # 4) Enrichissement LLM (anonymisé) sur les événements les plus à risque
    llm_used = 0
    if use_llm and api_key:
        notify(0.45, "Agent Évaluation : analyse IA des écarts (données pseudonymisées)…")
        try:
            llm = build_llm(api_key, model)
            targets = sorted([r for r in results if r["rules"]], key=lambda r: -r["score"])[:max_llm_events]
            if len([r for r in results if r["rules"]]) > max_llm_events:
                warnings.append(f"Analyse IA limitée aux {max_llm_events} écarts les plus graves ; les autres restent évalués par les règles.")

            def work(r):
                prompt = _event_prompt(anon_events[r["idx"] - 1], r["retrieved"], r["rules"])
                return r["idx"], parse_json(invoke_text(llm, prompt))

            aborted = False
            with ThreadPoolExecutor(max_workers=3) as pool:
                futures = [pool.submit(work, r) for r in targets]
                done = 0
                for fut in as_completed(futures):
                    done += 1
                    notify(0.45 + 0.4 * done / max(len(futures), 1), f"Analyse IA : {done}/{len(futures)} écarts traités…")
                    try:
                        idx, data = fut.result()
                    except LLMAuthError:
                        aborted = True
                        continue
                    except Exception as exc:  # noqa: BLE001
                        warnings.append(f"Appel IA en échec ({type(exc).__name__}) : repli sur les règles.")
                        continue
                    if not data:
                        continue
                    r = results[idx - 1]
                    lvl = str(data.get("niveau_risque", "")).upper().replace("É", "E")
                    if lvl in LEVELS:
                        r["level"] = _max_level(r["rule_level"], lvl)
                    if data.get("justification"):
                        r["justification"] = anon.restore(str(data["justification"]))
                    if data.get("recommandation"):
                        r["recommendation"] = anon.restore(str(data["recommandation"]))
                    r["llm"] = data
                    r["mode"] = "IA + règles"
                    llm_used += 1
            if aborted:
                warnings.append("Clé API Groq refusée : l'audit a été conduit avec le moteur de règles uniquement.")
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"LLM indisponible ({type(exc).__name__}) : audit conduit avec le moteur de règles.")

    # 5) Agent Reporting : statistiques + synthèse exécutive
    notify(0.9, "Agent Reporting : consolidation et rédaction de la synthèse exécutive…")
    by_level = {lv: sum(1 for r in results if r["level"] == lv and r["non_conforme"]) for lv in LEVELS}
    total = len(results)
    nonconform = sum(1 for r in results if r["non_conforme"])
    stats = {
        "total": total,
        "nonconform": nonconform,
        "by_level": by_level,
        "crit_high": by_level["CRITIQUE"] + by_level["ELEVE"],
        "compliance_rate": round(100 * (total - nonconform) / max(total, 1), 1),
        "frameworks": _framework_scores(results),
    }
    summary = _fallback_summary(stats)
    if llm_used:
        try:
            top = sorted([r for r in results if r["non_conforme"]], key=lambda r: -r["score"])[:6]
            digest = "\n".join(f"- [{r['level']}] {anon.text(r['log']['action'])} : {anon.text(r['justification'])}" for r in top)
            prompt = (f"Rédige en français une synthèse exécutive de 5 phrases maximum pour le Comité d'Audit de NFC Bank.\n"
                      f"Chiffres : {total} événements, {nonconform} non-conformités, {by_level['CRITIQUE']} critiques, "
                      f"{by_level['ELEVE']} élevées, conformité {stats['compliance_rate']} %.\nPrincipaux constats :\n{digest}\n"
                      "Style : factuel, sans jargon superflu, termine par la priorité d'action n°1. Aucun titre, aucune liste.")
            summary = anon.restore(invoke_text(build_llm(api_key, model, 0.2), prompt, retries=2)).strip() or summary
        except Exception:  # noqa: BLE001
            pass

    elapsed = round(time.perf_counter() - t0, 1)
    notify(1.0, "Audit terminé.")
    return {
        "results": results,
        "stats": stats,
        "summary": summary,
        "warnings": warnings,
        "meta": {
            "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "elapsed_s": elapsed,
            "llm_events": llm_used,
            "model": model if llm_used else "moteur de règles",
            "rag_backend": retriever.backend,
            "rag_note": retriever.note,
        },
    }
