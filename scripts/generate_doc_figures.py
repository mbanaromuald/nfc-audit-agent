"""Génère les figures de la documentation à partir d'une exécution réelle du moteur d'audit.

Usage : python scripts/generate_doc_figures.py   (nécessite matplotlib : pip install -r requirements-dev.txt)
Les images sont écrites dans docs/images/. Mode « règles seules » : reproductible, sans clé API.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch, Wedge

from nfc_audit.config import FRAMEWORKS, LEVEL_COLORS, LEVEL_LABELS, LEVELS, PALETTE
from nfc_audit.ingestion import sample_logs
from nfc_audit.pipeline import run_audit
from nfc_audit.rag import NormRetriever
from nfc_audit.reporting import to_html

OUT = ROOT / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)
APPROVED = {"CHG-2025-089", "CHG-2025-091", "INC-2025-3312", "HR-2025-0412", "REQ-2025-1180"}
P = PALETTE
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": P["line"], "axes.labelcolor": P["graphite"],
                     "text.color": P["ink"], "xtick.color": P["graphite"], "ytick.color": P["graphite"]})

audit = run_audit(sample_logs(), NormRetriever(prefer_embeddings=False), use_llm=False, approved_tickets=APPROVED)
res, st = audit["results"], audit["stats"]


def lvl_color(r):
    return LEVEL_COLORS[r["level"]] if r["non_conforme"] else P["ok"]


# ---------------------------------------------------------------- 1. tableau de bord
fig = plt.figure(figsize=(15, 8.4), facecolor="#F7F7F7")
gs = fig.add_gridspec(2, 12, height_ratios=[0.8, 2.2], hspace=0.28, wspace=1.2, left=0.04, right=0.97, top=0.9, bottom=0.07)
fig.suptitle("NFC-AuditAgent · Tableau de bord de l'audit de démonstration", x=0.04, ha="left", fontsize=17,
             fontweight="bold", color=P["graphite"])
kpis = [("Événements analysés", str(st["total"]), P["red"]),
        ("Écarts critiques / élevés", str(st["crit_high"]), P["crit"]),
        ("Taux de conformité", f"{st['compliance_rate']:g} %", P["ok"]),
        ("Délai d'analyse (règles)", "< 1 s", P["graphite"])]
for i, (label, value, color) in enumerate(kpis):
    ax = fig.add_subplot(gs[0, i * 3:(i + 1) * 3]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.06", fc="white", ec=P["line"], transform=ax.transAxes))
    ax.add_patch(Wedge((0, 1), 0.28, 270, 360, fc=color, transform=ax.transAxes, clip_on=False))
    ax.text(0.08, 0.46, value, fontsize=30, fontweight="bold", color=P["ink"], va="center")
    ax.text(0.08, 0.13, label, fontsize=11, color=P["graphite"], fontweight="bold")

# jauge
ax = fig.add_subplot(gs[1, 0:3]); ax.set_aspect("equal"); ax.axis("off")
pct = st["compliance_rate"]; col = P["ok"] if pct >= 85 else P["warn"] if pct >= 60 else P["crit"]
ax.add_patch(Wedge((0, 0), 1, 0, 360, width=0.28, fc="#E6E7E7"))
ax.add_patch(Wedge((0, 0), 1, 90 - 3.6 * pct, 90, width=0.28, fc=col))
ax.text(0, 0.05, f"{pct:g} %", ha="center", va="center", fontsize=28, fontweight="bold")
ax.text(0, -0.28, "conformité globale", ha="center", fontsize=10.5, color=P["graphite"])
ax.set_xlim(-1.15, 1.15); ax.set_ylim(-1.3, 1.3)
ax.set_title("Conformité globale", loc="left", fontsize=12.5, fontweight="bold", color=P["graphite"])

# référentiels
ax = fig.add_subplot(gs[1, 4:8]); ax.set_facecolor("none")
labels = [l for _, l in FRAMEWORKS][::-1]; vals = [st["frameworks"][k] for k, _ in FRAMEWORKS][::-1]
cols = [P["ok"] if v >= 85 else P["warn"] if v >= 60 else P["crit"] for v in vals]
ax.barh(labels, [100] * 4, color="#E6E7E7", height=0.45); ax.barh(labels, vals, color=cols, height=0.45)
for y, v in enumerate(vals):
    ax.text(v + 1.5, y, f"{v:g} %", va="center", fontweight="bold", fontsize=10.5)
ax.set_xlim(0, 112); ax.set_xticks([]); [s.set_visible(False) for s in ax.spines.values()]
ax.set_title("Conformité par référentiel", loc="left", fontsize=12.5, fontweight="bold", color=P["graphite"])

# matrice
ax = fig.add_subplot(gs[1, 8:12]); ax.set_facecolor("none")
counts = Counter((r["impact"], r["probability"]) for r in res if r["non_conforme"])
for imp in range(1, 6):
    for prob in range(1, 6):
        sc = imp * prob
        key = "CRITIQUE" if sc >= 20 else "ELEVE" if sc >= 12 else "MOYEN" if sc >= 6 else "FAIBLE"
        n = counts.get((imp, prob), 0)
        ax.add_patch(plt.Rectangle((prob - 0.46, imp - 0.46), 0.92, 0.92, fc=LEVEL_COLORS[key], alpha=1 if n else 0.16, ec="none"))
        if n:
            ax.text(prob, imp, str(n), ha="center", va="center", color="white", fontsize=15, fontweight="bold")
ax.set_xlim(0.4, 5.6); ax.set_ylim(0.4, 5.6); ax.set_xticks(range(1, 6)); ax.set_yticks(range(1, 6))
ax.set_xlabel("Probabilité →"); ax.set_ylabel("Impact →"); [s.set_visible(False) for s in ax.spines.values()]
ax.set_title("Matrice de risques (événements)", loc="left", fontsize=12.5, fontweight="bold", color=P["graphite"])
fig.savefig(OUT / "01_tableau_de_bord.png", dpi=130); plt.close(fig)

# ---------------------------------------------------------------- 2. scores par événement
order = sorted(res, key=lambda r: (r["score"], -r["idx"]))
fig, ax = plt.subplots(figsize=(13, 7.2), facecolor="#F7F7F7")
names = [f"{r['log']['timestamp'][11:19]}  {r['log']['action'][:52]}" for r in order]
ypos = list(range(len(order)))
ax.barh(ypos, [r["score"] for r in order], color=[lvl_color(r) for r in order], height=0.62)
ax.set_yticks(ypos); ax.set_yticklabels(names)
for y, r in enumerate(order):
    tag = ", ".join(x["code"] for x in r["rules"]) or "conforme"
    ax.text(r["score"] + 0.4, y, f"{r['score'] if r['non_conforme'] else '–'}  ·  {tag}", va="center", fontsize=8.8, color=P["graphite"])
for x, lab in ((6, "Moyen"), (12, "Élevé"), (20, "Critique")):
    ax.axvline(x, color=P["gray"], ls="--", lw=1); ax.text(x + 0.15, len(order) - 0.45, f"≥ {x} {lab}", fontsize=8.5, color="#6A6C6C")
ax.set_xlim(0, 44); ax.set_ylim(-0.7, len(order) - 0.1); ax.set_xlabel("Score de risque = impact × probabilité (événements conformes : score de base 1, non affiché)")
[ax.spines[s].set_visible(False) for s in ("top", "right")]
ax.set_title("Score de risque de chacun des 16 événements analysés", loc="left", fontsize=14, fontweight="bold", color=P["graphite"])
fig.tight_layout(); fig.savefig(OUT / "02_scores_par_evenement.png", dpi=130); plt.close(fig)

# ---------------------------------------------------------------- 3. chronologie
df = pd.DataFrame([{"t": pd.to_datetime(r["log"]["timestamp"]), "sys": r["log"]["source_sys"], "r": r} for r in res])
fig, ax = plt.subplots(figsize=(13, 5.2), facecolor="#F7F7F7")
lane = {"Active Directory": 1, "Oracle DB Prod": 0}
for _, row in df.iterrows():
    r = row["r"]
    ax.scatter(row["t"], lane[row["sys"]], s=70 + r["score"] * 14, color=lvl_color(r), edgecolor="white", linewidth=1.5, zorder=3)
t = lambda hm: pd.to_datetime("2025-02-17 " + hm)
ax.axvspan(t("03:11"), t("03:16"), color=P["crit"], alpha=0.10)
ax.annotate("Rafale de 5 échecs\npuis connexion réussie", (t("03:13"), 1), xytext=(t("04:50"), 1.42), fontsize=9.5,
            arrowprops=dict(arrowstyle="-", color=P["gray"]), color=P["graphite"])
ax.annotate("", xy=(t("08:30"), 0.04), xytext=(t("08:14"), 0.96), arrowprops=dict(arrowstyle="->", color=P["crit"], lw=2))
ax.text(t("08:40"), 0.52, "Corrélation : compte privilégié créé sans ticket\npuis ALTER TABLE en production 15 min plus tard", fontsize=9.5, color=P["crit"], va="center")
ax.annotate("DROP TABLE\nsans RFC", (t("14:15"), 0), xytext=(t("14:30"), -0.5), fontsize=9.5, color=P["graphite"], arrowprops=dict(arrowstyle="-", color=P["gray"]))
ax.annotate("Groupe d'admins\nticket invalide", (t("22:47"), 1), xytext=(t("19:30"), 1.42), fontsize=9.5, color=P["graphite"], arrowprops=dict(arrowstyle="-", color=P["gray"]))
ax.set_yticks([0, 1]); ax.set_yticklabels(["Oracle DB Prod", "Active Directory"]); ax.set_ylim(-0.85, 1.85)
ax.set_xlim(t("02:30"), t("23:40")); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Hh")); ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
ax.grid(axis="x", color=P["line"]); [ax.spines[s].set_visible(False) for s in ("top", "right", "left")]
handles = [plt.Line2D([], [], marker="o", ls="", color=c, markersize=10, label=l) for l, c in
           [("Conforme", P["ok"])] + [(LEVEL_LABELS[k], LEVEL_COLORS[k]) for k in ("MOYEN", "ELEVE", "CRITIQUE")]]
ax.legend(handles=handles, loc="lower left", ncol=4, frameon=False, bbox_to_anchor=(0, -0.2))
ax.set_title("Chronologie des événements du 17/02/2025 (la taille du point suit le score de risque)", loc="left", fontsize=13.5, fontweight="bold", color=P["graphite"])
fig.tight_layout(); fig.savefig(OUT / "03_chronologie.png", dpi=130); plt.close(fig)

# ---------------------------------------------------------------- 4. règles déclenchées + normes touchées
rules_count = Counter(x["code"] for r in res for x in r["rules"])
norm_count = Counter(n["id"] for r in res for n in r["norms"])
fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5.4), facecolor="#F7F7F7", gridspec_kw={"width_ratios": [1, 1.1]})
items = sorted(rules_count.items(), key=lambda kv: kv[1])
a1.barh([k for k, _ in items], [v for _, v in items], color=P["red"], height=0.55)
for y, (_, v) in enumerate(items):
    a1.text(v + 0.04, y, str(v), va="center", fontweight="bold")
a1.set_title("Règles déclenchées", loc="left", fontsize=13, fontweight="bold", color=P["graphite"]); a1.set_xticks([])
items = sorted(norm_count.items(), key=lambda kv: kv[1])
a2.barh([k for k, _ in items], [v for _, v in items], color=P["graphite"], height=0.55)
for y, (_, v) in enumerate(items):
    a2.text(v + 0.06, y, str(v), va="center", fontweight="bold")
a2.set_title("Exigences normatives enfreintes (nb d'événements)", loc="left", fontsize=13, fontweight="bold", color=P["graphite"]); a2.set_xticks([])
for a in (a1, a2):
    [a.spines[s].set_visible(False) for s in ("top", "right", "bottom")]
fig.tight_layout(); fig.savefig(OUT / "04_regles_et_normes.png", dpi=130); plt.close(fig)

# ---------------------------------------------------------------- 5. rapport HTML exporté (source pour capture)
(OUT / "rapport_exporte.html").write_bytes(to_html(audit))

# ---------------------------------------------------------------- sortie texte pour la documentation
print("STATS", st)
print("| # | Heure | Système | Action | Ticket | Niveau | Score | Règles |\n|---|---|---|---|---|---|---|---|")
for r in res:
    l = r["log"]
    print(f"| {r['idx']} | {l['timestamp'][11:19]} | {l['source_sys']} | {l['action']} | {l['ticket_ref']} | "
          f"{LEVEL_LABELS[r['level']] if r['non_conforme'] else 'Conforme'} | {r['score'] if r['non_conforme'] else '–'} | "
          f"{', '.join(x['code'] for x in r['rules']) or '–'} |")
