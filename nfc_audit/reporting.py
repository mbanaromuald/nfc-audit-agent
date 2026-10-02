"""Exports du rapport exécutif : HTML autonome (imprimable en PDF), CSV et JSON."""
from __future__ import annotations

import html as _html
import json

import pandas as pd

from .config import BRAND, FRAMEWORKS, LEVEL_COLORS, LEVEL_LABELS, LEVELS, PALETTE, fmt_seconds
from .ui import logo_data_uri

e = _html.escape


def to_dataframe(audit: dict) -> pd.DataFrame:
    rows = []
    for r in audit["results"]:
        log = r["log"]
        rows.append({
            "n": r["idx"], "horodatage": log["timestamp"], "systeme": log["source_sys"], "event_id": log["event_id"],
            "acteur": log["actor"], "cible": log["user_target"], "action": log["action"], "ticket": log["ticket_ref"],
            "non_conforme": "Oui" if r["non_conforme"] else "Non", "niveau": r["level"], "score": r["score"],
            "normes_enfreintes": " | ".join(f"{n['source']} {n['article']}" for n in r["norms"]),
            "constat": r["justification"], "recommandation": r["recommendation"], "mode": r["mode"],
        })
    return pd.DataFrame(rows)


def to_csv(audit: dict) -> bytes:
    return to_dataframe(audit).to_csv(index=False, sep=";").encode("utf-8-sig")


def to_json(audit: dict) -> bytes:
    payload = {
        "application": BRAND["app"], "organisation": BRAND["bank_long"], "developpeur": BRAND["developer"],
        "meta": audit["meta"], "statistiques": audit["stats"], "synthese": audit["summary"],
        "constats": to_dataframe(audit).to_dict("records"),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")


def to_html(audit: dict) -> bytes:
    s, m = audit["stats"], audit["meta"]
    findings = sorted([r for r in audit["results"] if r["non_conforme"]], key=lambda r: -r["score"])
    rows = ""
    for r in findings:
        log = r["log"]
        rows += (f"<tr><td><span class='p' style='background:{LEVEL_COLORS[r['level']]}'>{e(LEVEL_LABELS[r['level']])}</span></td>"
                 f"<td>{e(log['timestamp'])}<br><small>{e(log['source_sys'])}</small></td>"
                 f"<td><b>{e(log['action'])}</b><br><small>{e(log['actor'])} → {e(log['user_target'])} · ticket {e(log['ticket_ref'])}</small></td>"
                 f"<td>{e(r['justification'])}<br><small><b>Normes :</b> "
                 f"{e(' ; '.join(n['source'] + ' ' + n['article'].split(' – ')[0] for n in r['norms']))}</small></td>"
                 f"<td>{e(r['recommendation'])}</td></tr>")
    fw = "".join(f"<tr><td>{e(lbl)}</td><td><b>{s['frameworks'].get(k, 100):g} %</b></td></tr>" for k, lbl in FRAMEWORKS)
    P = PALETTE
    doc = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Rapport d'audit – {e(BRAND['app'])}</title>
<style>
body{{font-family:Arial,Helvetica,sans-serif;color:{P['ink']};margin:0;background:#F6F9FD}}
.wrap{{max-width:1100px;margin:0 auto;padding:28px}}
.head{{background:linear-gradient(135deg,{P['graphite']},#3A3C3C);color:#fff;border-radius:16px;padding:26px 30px;border-bottom:6px solid {P['red']}}}
.proto{{background:{P['red']};color:#fff;text-align:center;font-size:12px;font-weight:700;letter-spacing:.06em;padding:7px;border-radius:10px;margin-bottom:12px}}
.head img{{height:64px;background:#fff;border-radius:8px;padding:6px}} .head h1{{margin:16px 0 4px;font-size:28px}}
.head small{{color:#C9D8EE}}
.kp{{display:flex;gap:12px;margin:18px 0}} .k{{flex:1;background:#fff;border:1px solid {P['line']};border-radius:12px;padding:14px;border-left:5px solid {P['red']}}}
.k b{{font-size:26px;display:block}} .k span{{font-size:12px;color:#475569}}
h2{{color:{P['graphite']};margin-top:26px}} .sum{{background:#fff;border-left:6px solid {P['red']};padding:16px 20px;border-radius:10px;line-height:1.7}}
table{{width:100%;border-collapse:collapse;background:#fff;font-size:13px;table-layout:fixed}}
th:nth-child(1){{width:80px}} th:nth-child(2){{width:112px}} th:nth-child(3){{width:19%}} th:nth-child(4){{width:33%}}
th{{background:{P['graphite']};color:#fff;text-align:left;padding:9px}} td{{padding:9px;border-bottom:1px solid {P['line']};vertical-align:top}}
.p{{color:#fff;border-radius:99px;padding:2px 10px;font-weight:700;font-size:12px}} small{{color:#64748B}}
.foot{{text-align:center;color:#64748B;font-size:12px;margin-top:26px}}
@media print{{body{{background:#fff}}.wrap{{padding:0}}}}
</style></head><body><div class="wrap">
<div class="proto">{e(BRAND["proto_short"])}</div>
<div class="head"><img src="{logo_data_uri()}" alt="Logo {e(BRAND['bank'])}"><h1>Rapport exécutif de conformité SI</h1>
<small>{e(BRAND['bank_long'])} · Généré le {e(m['generated_at'])} · Moteur : {e(m['model'])} · Recherche : {e(m['rag_backend'])}</small></div>
<div class="kp"><div class="k"><b>{s['total']}</b><span>Événements analysés</span></div>
<div class="k" style="border-color:{P['crit']}"><b>{s['crit_high']}</b><span>Écarts critiques / élevés</span></div>
<div class="k" style="border-color:{P['ok']}"><b>{s['compliance_rate']:g} %</b><span>Taux de conformité</span></div>
<div class="k"><b>{fmt_seconds(m['elapsed_s'])}</b><span>Délai d'analyse</span></div></div>
<h2>Synthèse</h2><div class="sum">{e(audit['summary'])}</div>
<h2>Conformité par référentiel</h2><table><tr><th>Référentiel</th><th>Taux</th></tr>{fw}</table>
<h2>Constats détaillés ({len(findings)})</h2>
<table><tr><th>Niveau</th><th>Horodatage</th><th>Événement</th><th>Constat</th><th>Plan d'action</th></tr>{rows or '<tr><td colspan=5>Aucun écart.</td></tr>'}</table>
<div class="foot">{e(BRAND['app'])} · Développé par <b>{e(BRAND['developer'])}</b> · {e(BRAND['bank_long'])}<br>{e(BRAND['proto'])}<br>
Pour un PDF : ouvrir ce fichier dans le navigateur puis Imprimer → Enregistrer au format PDF.</div>
</div></body></html>"""
    return doc.encode("utf-8")
