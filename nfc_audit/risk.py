"""Agent Évaluation des Risques : moteur de règles déterministe + corrélation d'événements.

Chaque règle produit un couple (impact, probabilité) sur une échelle 1-5.
Score = impact × probabilité  ->  CRITIQUE (≥20), ELEVE (≥12), MOYEN (≥6), FAIBLE (<6).
Le LLM peut relever un niveau mais jamais abaisser celui établi par les règles.
"""
from __future__ import annotations

import re
from datetime import timedelta

import pandas as pd

AD_ACCOUNT = {4720, 4722, 4724, 4725, 4726, 4738}
AD_GROUP = {4728, 4732, 4756}
TICKET_RE = re.compile(r"^[A-Z]{2,6}-(\d{4}-)?\d{2,8}$")
PRIV_RE = re.compile(r"privil|admin|dba|root|sysadmin|domain admins|superuser|sudo", re.I)
DDL_RE = re.compile(r"\b(ALTER|DROP|TRUNCATE|CREATE|GRANT|REVOKE)\b", re.I)
DML_RE = re.compile(r"\b(UPDATE|DELETE|INSERT|MERGE)\b", re.I)
REACT_RE = re.compile(r"r[ée]activ|inactif|dormant", re.I)
CREATE_RE = re.compile(r"cr[ée]ation|create", re.I)

RECOMMENDATIONS = {
    "PRIV_NO_TICKET": "Suspendre le compte ou le droit concerné, retrouver l'approbation nominative (RFC/ITSM) ou révoquer, puis documenter la régularisation.",
    "PRIV_TICKET_INVALID": "Vérifier la validité du ticket auprès de l'ITSM, exiger une RFC approuvée et régulariser le dossier d'autorisation.",
    "REACTIVATION": "Désactiver le compte jusqu'à validation de la demande par le responsable métier ; revoir la liste des comptes dormants (>90 jours).",
    "ACCOUNT_NO_TICKET": "Rattacher l'opération à une demande ITSM approuvée ou la corriger ; renforcer le contrôle préventif sur les opérations manuelles.",
    "DB_NO_TICKET": "Auditer l'objet modifié, comparer à la dernière sauvegarde, restaurer si nécessaire et ouvrir une RFC de régularisation.",
    "DB_TICKET_INVALID": "Contrôler la RFC citée (existence, périmètre, approbation) et sanctionner tout contournement du processus de changement.",
    "TICKET_NOT_APPROVED": "Le ticket n'est pas approuvé dans l'ITSM : traiter comme un changement non autorisé et escalader au RSSI.",
    "SELF_ELEVATION": "Révoquer immédiatement l'élévation, séparer les rôles demandeur/approbateur et lancer une revue des droits du compte.",
    "NEW_ACCOUNT_PROD": "Bloquer le compte, examiner l'ensemble de ses actions et vérifier l'intégrité des données de production concernées.",
    "BRUTE_FORCE": "Verrouiller le compte ciblé, filtrer l'adresse source, ouvrir un incident de sécurité et forcer le renouvellement du secret.",
    "LOGIN_AFTER_BRUTE": "Considérer le compte comme compromis : fermer les sessions, réinitialiser les identifiants et ouvrir un incident majeur.",
}


def level_from_score(score: int) -> str:
    if score >= 20:
        return "CRITIQUE"
    if score >= 12:
        return "ELEVE"
    if score >= 6:
        return "MOYEN"
    return "FAIBLE"


def has_ticket(value) -> bool:
    return str(value).strip().lower() not in {"", "n/a", "na", "none", "null", "-", "nan", "aucun"}


def _rule(code, title, impact, prob, norms, detail):
    return {"code": code, "title": title, "impact": impact, "probability": prob,
            "norm_ids": norms, "detail": detail, "recommendation": RECOMMENDATIONS[code]}


def _kind(row) -> str:
    eid = int(row["event_id"]) if pd.notna(row["event_id"]) else None
    src = str(row["source_sys"]).lower()
    text = f"{row['action']} {row['resource']}"
    if eid == 4625:
        return "login_fail"
    if eid == 4624:
        return "login_ok"
    if eid in AD_GROUP or ("groupe" in text.lower() or "group" in text.lower()) and "active directory" in src:
        return "group"
    if eid in AD_ACCOUNT or "compte" in text.lower() and "active directory" in src:
        return "account"
    if any(k in src for k in ("oracle", "db", "sql", "postgres", "base")) or DDL_RE.search(text) or DML_RE.search(text):
        return "db"
    return "other"


def _off_hours(ts) -> bool:
    if pd.isna(ts):
        return False
    return ts.hour < 6 or ts.hour >= 20 or ts.weekday() >= 5


def evaluate(df: pd.DataFrame, approved_tickets: set[str] | None = None) -> list[list[dict]]:
    """Retourne, pour chaque ligne du DataFrame, la liste des règles déclenchées."""
    ts = pd.to_datetime(df["timestamp"], errors="coerce")
    kinds = [_kind(r) for _, r in df.iterrows()]
    results: list[list[dict]] = [[] for _ in range(len(df))]

    # Index de corrélation : comptes créés (cible -> (horodatage, ticket présent))
    created: dict[str, tuple[pd.Timestamp, bool]] = {}
    for i, (_, r) in enumerate(df.iterrows()):
        if kinds[i] == "account" and (r["event_id"] == 4720 or CREATE_RE.search(str(r["action"]))) and pd.notna(ts.iloc[i]):
            created[str(r["user_target"])] = (ts.iloc[i], has_ticket(r["ticket_ref"]))

    for i, (_, r) in enumerate(df.iterrows()):
        kind, rules = kinds[i], results[i]
        text = f"{r['action']} {r['resource']} {r['user_target']}"
        ticket = str(r["ticket_ref"]).strip()
        needs_ticket = kind in {"account", "group", "db"}

        if needs_ticket:
            privileged = kind == "group" and bool(PRIV_RE.search(text)) or (kind == "account" and bool(PRIV_RE.search(str(r["action"]))))
            react = kind == "account" and bool(REACT_RE.search(str(r["action"])))
            ddl = kind == "db" and bool(DDL_RE.search(str(r["action"])))
            dml = kind == "db" and bool(DML_RE.search(str(r["action"]))) and not ddl
            ad_norms = ["COBAC-12", "ISO-A5.18", "COBIT-DSS05.04", "ITIL-CHG"]
            priv_norms = ["COBAC-12", "ISO-A8.2", "ISO-A5.18", "COBIT-DSS05.04", "ITIL-CHG"]
            db_norms = ["ITIL-CHG", "ISO-A8.32", "COBIT-BAI06", "COBAC-12"]

            if not has_ticket(ticket):
                if privileged:
                    rules.append(_rule("PRIV_NO_TICKET", "Privilège accordé sans ticket approuvé", 5, 4, priv_norms,
                                       f"Opération à privilèges « {r['action']} » réalisée par {r['actor']} sans référence ITSM."))
                elif react:
                    rules.append(_rule("REACTIVATION", "Compte inactif réactivé sans ticket", 4, 4, ad_norms,
                                       f"Réactivation de {r['user_target']} par {r['actor']} sans demande approuvée."))
                elif kind in {"account", "group"}:
                    imp = 2 if r["event_id"] == 4725 else 3
                    rules.append(_rule("ACCOUNT_NO_TICKET", "Gestion de compte sans ticket", imp, 3, ad_norms,
                                       f"« {r['action']} » sur {r['user_target']} sans référence ITSM."))
                elif ddl or dml:
                    rules.append(_rule("DB_NO_TICKET", "Modification de base de production sans RFC",
                                       5 if ddl else 4, 4, db_norms,
                                       f"« {r['action']} » exécuté par {r['actor']} sur {r['resource'] or 'la base'} sans RFC."))
            else:
                if not TICKET_RE.match(ticket):
                    code = "DB_TICKET_INVALID" if kind == "db" else "PRIV_TICKET_INVALID"
                    imp = 5 if (privileged or ddl) else 4 if (react or dml) else 3
                    rules.append(_rule(code, "Référence de ticket au format invalide", imp, 3,
                                       db_norms if kind == "db" else priv_norms,
                                       f"La référence « {ticket} » ne correspond à aucun format ITSM valide."))
                elif approved_tickets is not None and ticket not in approved_tickets:
                    rules.append(_rule("TICKET_NOT_APPROVED", "Ticket absent ou non approuvé dans l'ITSM", 4, 4,
                                       db_norms if kind == "db" else priv_norms,
                                       f"Le ticket {ticket} n'est pas approuvé dans l'export ITSM fourni."))

            if kind == "group" and str(r["actor"]) == str(r["user_target"]) and r["actor"]:
                rules.append(_rule("SELF_ELEVATION", "Auto-attribution de droits (séparation des fonctions)", 5, 5,
                                   ["COBAC-12", "ISO-A8.2", "COBIT-DSS05.04"],
                                   f"{r['actor']} s'est lui-même ajouté à « {r['resource'] or r['action']} »."))

            # Corrélation : compte récent sans ticket qui agit en production ou sur des groupes
            if kind in {"db", "group"} and str(r["actor"]) in created and pd.notna(ts.iloc[i]):
                t0, tick_ok = created[str(r["actor"])]
                if timedelta(0) <= ts.iloc[i] - t0 <= timedelta(hours=24) and (not tick_ok):
                    mins = int((ts.iloc[i] - t0).total_seconds() // 60)
                    rules.append(_rule("NEW_ACCOUNT_PROD", "Compte créé sans ticket agissant en production", 5, 5,
                                       ["COBAC-12", "ISO-A8.2", "ISO-A8.32", "COBIT-DSS05.04", "COBIT-BAI06", "ITIL-CHG"],
                                       f"Le compte {r['actor']} (créé sans ticket {mins} min plus tôt) a exécuté « {r['action']} » : "
                                       "chaîne création de privilège → action en production non autorisée."))

        # Authentification : rafales d'échecs puis succès
        if kind in {"login_fail", "login_ok"} and pd.notna(ts.iloc[i]):
            key = str(r["user_target"] or r["actor"])
            window = [j for j in range(i + 1) if kinds[j] == "login_fail"
                      and str(df.iloc[j]["user_target"] or df.iloc[j]["actor"]) == key
                      and pd.notna(ts.iloc[j]) and timedelta(0) <= ts.iloc[i] - ts.iloc[j] <= timedelta(minutes=10)]
            if kind == "login_fail" and len(window) >= 5:
                rules.append(_rule("BRUTE_FORCE", "Rafale d'échecs d'authentification", 3, 4,
                                   ["ISO-A8.15", "ISO-A8.16", "COBIT-DSS05.07", "ITIL-INC"],
                                   f"{len(window)} échecs en moins de 10 min pour {key} depuis {r['ip_address'] or 'source inconnue'}."))
            if kind == "login_ok" and len(window) >= 5:
                rules.append(_rule("LOGIN_AFTER_BRUTE", "Connexion réussie après rafale d'échecs", 5, 4,
                                   ["ISO-A8.15", "ISO-A8.16", "COBIT-DSS05.07", "ITIL-INC", "COBAC-12"],
                                   f"Succès d'authentification pour {key} juste après {len(window)} échecs : compromission possible."))

        # Circonstance aggravante : hors heures ouvrées sur opération sensible
        if rules and kind in {"account", "group", "db"} and _off_hours(ts.iloc[i]):
            for rule in rules:
                if rule["probability"] < 5:
                    rule["probability"] += 1
                    rule["detail"] += " Opération réalisée hors heures ouvrées."
                    break
    return results
