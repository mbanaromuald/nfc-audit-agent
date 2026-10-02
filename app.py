"""NFC-AuditAgent – Plateforme multi-agents de contrôle continu de la conformité SI.

Développé par Romuald Arthur MBANA MEDJO pour NFC Bank.
Lancement : streamlit run app.py
"""
from __future__ import annotations

import hmac
import os
import uuid

import pandas as pd
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # noqa: BLE001
    pass

from nfc_audit import ui
from nfc_audit.config import fmt_seconds, BRAND, DEFAULT_MODEL, GROQ_MODELS, LEVEL_COLORS, LEVEL_LABELS, LEVELS, PALETTE
from nfc_audit.ingestion import load_files, load_itsm_tickets, sample_itsm_csv, sample_log_text, sample_logs
from nfc_audit.knowledge import NORMS
from nfc_audit.pipeline import run_audit
from nfc_audit.rag import NormRetriever
from nfc_audit.reporting import to_csv, to_html, to_json

_icon = ui.logo_path()
try:
    from PIL import Image
    _icon = Image.open(_icon) if _icon else "🛡️"
except Exception:  # noqa: BLE001
    _icon = "🛡️"
st.set_page_config(page_title=f"{BRAND['app']} | Prototype {BRAND['bank']}", page_icon=_icon, layout="wide")
ui.inject_css()


def show_df(df: pd.DataFrame) -> None:
    try:
        st.dataframe(df, width="stretch", hide_index=True)
    except TypeError:
        st.dataframe(df, use_container_width=True, hide_index=True)


def primary_button(label: str, key: str, disabled: bool = False) -> bool:
    try:
        return st.button(label, key=key, type="primary", width="stretch", disabled=disabled)
    except TypeError:
        return st.button(label, key=key, type="primary", use_container_width=True, disabled=disabled)


def gate() -> None:
    """Mot de passe d'accès facultatif (variable APP_PASSWORD) avant exposition via ngrok."""
    expected = os.getenv("APP_PASSWORD", "")
    if not expected or st.session_state.get("auth_ok"):
        return
    ui.proto_ribbon()
    ui.hero()
    st.write("")
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        ui.section("Accès réservé", "Saisissez le mot de passe communiqué par l'équipe Sécurité du SI.")
        pwd = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter", type="primary"):
            if hmac.compare_digest(pwd, expected):
                st.session_state["auth_ok"] = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect. Vérifiez la saisie ou contactez le RSSI.")
    st.stop()


gate()

# ----------------------------------------------------------------- état de session
ss = st.session_state
ss.setdefault("session_id", uuid.uuid4().hex[:8])
ss.setdefault("logs", sample_logs())
ss.setdefault("source_label", "Jeu de démonstration (16 événements AD / Oracle)")
ss.setdefault("approved", {"CHG-2025-089", "CHG-2025-091", "INC-2025-3312", "HR-2025-0412", "REQ-2025-1180"})
ss.setdefault("audit", None)

# ----------------------------------------------------------------- barre latérale
ui.sidebar_brand()
st.sidebar.markdown("### Configuration")
api_key = st.sidebar.text_input("Clé API Groq", type="password", value=os.getenv("GROQ_API_KEY", ""),
                                help="Utilisée uniquement pour l'analyse IA. Les identités sont pseudonymisées avant l'envoi.")
mode = st.sidebar.radio("Moteur d'analyse", ["IA + règles", "Règles seules (hors ligne)"],
                        help="Le mode hors ligne n'envoie aucune donnée à l'extérieur.")
model = st.sidebar.selectbox("Modèle Groq", GROQ_MODELS, index=GROQ_MODELS.index(DEFAULT_MODEL))
max_llm = st.sidebar.slider("Écarts analysés par l'IA (max)", 5, 60, 25)
use_embeddings = st.sidebar.toggle("Recherche sémantique locale (MiniLM)", value=True,
                                   help="Active ChromaDB + all-MiniLM-L6-v2. Désactivez pour un démarrage instantané.")
st.sidebar.markdown("---")
st.sidebar.markdown("**Référentiels chargés**")
for lbl in ("COBAC R-2016/04", "ISO/IEC 27001:2022", "COBIT 2019", "ITIL v4"):
    st.sidebar.checkbox(lbl, value=True, disabled=True, key=f"fw_{lbl}")
st.sidebar.success("Pseudonymisation des identités active", icon="🔒")
ui.sidebar_footer()


@st.cache_resource(show_spinner=False)
def get_retriever(session_id: str, embeddings: bool) -> NormRetriever:
    return NormRetriever(prefer_embeddings=embeddings, session_id=f"{session_id}{int(embeddings)}")


ui.proto_ribbon()
ui.hero()
st.write("")
tab0, tab1, tab2, tab3, tab4 = st.tabs(["✨  Vision", "📥  Ingestion", "⚡  Pipeline d'audit", "📊  Rapport exécutif", "📚  Référentiels"])

# ----------------------------------------------------------------- Onglet 0 : vision
with tab0:
    ui.section("Pourquoi un agent d'audit continu ?", "Trois idées à retenir, puis un simulateur que vous pouvez régler en direct.")
    ui.pitch_cards()
    st.write("")
    ui.section("Simulez le gain pour NFC Bank", "Déplacez les curseurs : le calcul se met à jour immédiatement.")
    sa, sb = st.columns(2)
    with sa:
        ev_week = st.slider("Événements sensibles à contrôler par semaine", 50, 5000, 400, step=50)
        min_manual = st.slider("Minutes de contrôle manuel par événement", 1, 20, 6)
    with sb:
        default_rate = int(round(ss["audit"]["stats"]["nonconform"] / max(ss["audit"]["stats"]["total"], 1) * 100)) if ss.get("audit") else 20
        flag_rate = st.slider("Part d'événements signalés comme écarts (%)", 1, 60, max(1, min(default_rate, 60)),
                              help="Préréglé sur le dernier audit lancé, ou 20 % par défaut.")
        min_validate = st.slider("Minutes de validation d'un écart par l'auditeur", 2, 30, 10)
    manual_h = ev_week * min_manual / 60
    agent_h = ev_week * flag_rate / 100 * min_validate / 60
    st.markdown(ui.simulator(manual_h, agent_h), unsafe_allow_html=True)
    st.write("")
    ui.section("De prototype à production", "Ce qu'il faudrait mettre en place pour un déploiement réel.")
    ui.roadmap()

# ----------------------------------------------------------------- Onglet 1 : ingestion
with tab1:
    ui.section("Journaux à analyser", "Chargez vos extractions (.json, .csv, .log) ou utilisez le jeu de démonstration.")
    c1, c2 = st.columns([2, 1])
    with c1:
        files = st.file_uploader("Fichiers de journaux", type=["json", "csv", "log", "txt"], accept_multiple_files=True,
                                 label_visibility="collapsed")
        if files and primary_button(f"Analyser {len(files)} fichier(s) importé(s)", "load_files"):
            df, warns = load_files([(f.name, f.getvalue()) for f in files])
            for w in warns:
                st.warning(w)
            if df.empty:
                st.error("Aucun fichier exploitable. L'application attend des journaux d'événements (.json, .csv ou .log) "
                         "contenant au minimum un horodatage, un acteur et une action. Téléchargez un exemple ci-dessous pour voir le format.")
            else:
                ss["logs"], ss["source_label"], ss["audit"] = df, f"{len(files)} fichier(s) importé(s)", None
                st.success(f"{len(df)} événements normalisés. Passez à l'onglet « Pipeline d'audit » pour lancer l'analyse.")
        with st.expander("Besoin d'un fichier d'exemple ?"):
            st.caption("Trois formats équivalents, contenant le jeu de démonstration. Téléchargez-en un, puis réimportez-le ci-dessus.")
            _demo = sample_logs()
            e1, e2, e3 = st.columns(3)
            e1.download_button("Exemple .json", _demo.to_json(orient="records", force_ascii=False, indent=2),
                               "exemple_journaux.json", "application/json")
            e2.download_button("Exemple .csv", _demo.to_csv(index=False), "exemple_journaux.csv", "text/csv")
            e3.download_button("Exemple .log", sample_log_text(), "exemple_journaux.log", "text/plain")
    with c2:
        itsm = st.file_uploader("Export ITSM / Jira (facultatif)", type=["csv"],
                                help="Colonnes ticket_ref et status. Permet de vérifier que chaque ticket cité est bien approuvé.")
        if itsm is not None:
            try:
                ss["approved"] = load_itsm_tickets(itsm.getvalue())
                st.caption(f"{len(ss['approved'])} tickets approuvés reconnus.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Export ITSM illisible : {exc}")
        else:
            st.download_button("Télécharger un exemple ITSM", sample_itsm_csv(), "exemple_itsm.csv", "text/csv")
        if st.button("Revenir au jeu de démonstration"):
            ss["logs"], ss["source_label"], ss["audit"] = sample_logs(), "Jeu de démonstration (16 événements AD / Oracle)", None
            st.rerun()
    logs = ss["logs"]
    ui.kpis([("Événements", str(len(logs)), ss["source_label"], PALETTE["red"]),
             ("Systèmes sources", str(logs["source_sys"].nunique()), ", ".join(sorted(logs["source_sys"].unique()))[:48], PALETTE["graphite"]),
             ("Acteurs distincts", str(logs["actor"].nunique()), "Identités pseudonymisées avant envoi à l'IA", PALETTE["gray"]),
             ("Sans ticket ITSM", str(int((logs["ticket_ref"] == "N/A").sum())), "Candidats au rapprochement", PALETTE["high"])])
    show_df(logs)

# ----------------------------------------------------------------- Onglet 2 : pipeline
with tab2:
    ui.section("Exécution de l'audit automatisé", "Quatre agents spécialisés, supervisés par un orchestrateur central.")
    ui.agents_cards(done=ss["audit"] is not None)
    st.write("")
    want_llm = mode.startswith("IA")
    if want_llm and not api_key:
        st.markdown('<div class="note">Aucune clé Groq saisie : l\'audit sera conduit avec le moteur de règles uniquement. '
                    'Renseignez la clé dans le panneau latéral pour activer l\'analyse IA.</div>', unsafe_allow_html=True)
        st.write("")
    if primary_button("Démarrer l'audit de conformité", "run"):
        bar, txt = st.progress(0.0), st.empty()
        with st.spinner("Initialisation du moteur de recherche des référentiels…"):
            retriever = get_retriever(ss["session_id"], use_embeddings)

        def on_progress(frac: float, msg: str) -> None:
            bar.progress(min(frac, 1.0))
            txt.markdown(f"**{msg}**")

        ss["audit"] = run_audit(ss["logs"], retriever, api_key=api_key or None, model=model,
                                use_llm=want_llm and bool(api_key), approved_tickets=ss["approved"],
                                max_llm_events=max_llm, progress=on_progress)
        txt.empty()
        st.success("Audit terminé. Ouvrez l'onglet « Rapport exécutif ».")
        st.rerun()
    audit = ss["audit"]
    if audit:
        m = audit["meta"]
        st.caption(f"Dernier audit : {m['generated_at']} · {fmt_seconds(m['elapsed_s'])} · moteur : {m['model']} · recherche : {m['rag_backend']}")
        if m["rag_note"]:
            st.info(m["rag_note"])
        for w in audit["warnings"]:
            st.warning(w)

# ----------------------------------------------------------------- Onglet 3 : rapport
with tab3:
    audit = ss["audit"]
    if not audit:
        ui.section("Rapport exécutif de conformité", "Lancez d'abord l'audit depuis l'onglet « Pipeline d'audit ».")
        st.info("Aucun rapport disponible pour le moment.")
    else:
        s, m, results = audit["stats"], audit["meta"], audit["results"]
        ui.section("Rapport exécutif de conformité", f"Généré le {m['generated_at']} · {ss['source_label']}")
        ui.kpis([("Événements analysés", str(s["total"]), f"{m['llm_events']} enrichis par l'IA", PALETTE["red"]),
                 ("Écarts critiques / élevés", str(s["crit_high"]), f"{s['nonconform']} non-conformités au total", PALETTE["crit"]),
                 ("Taux de conformité", f"{s['compliance_rate']:g} %", "Événements sans écart", PALETTE["ok"]),
                 ui.mttd_card(m["elapsed_s"])])
        st.markdown(f'<div class="summary">{ui.e(audit["summary"])}</div>', unsafe_allow_html=True)
        st.write("")
        g1, g2, g3 = st.columns([1.1, 1.1, 1])
        with g1:
            st.markdown(ui.H(f'<div class="card"><div class="sec-title">Conformité globale</div><div class="gauge-wrap">'
                             f'{ui.gauge(s["compliance_rate"])}<div style="flex:1">'
                             + "".join(f'<div class="bar"><div class="t"><span>{LEVEL_LABELS[lv]}</span><span>{s["by_level"][lv]}</span></div>'
                                       f'<div class="tr"><i style="width:{100 * s["by_level"][lv] / max(s["nonconform"], 1)}%;--c:{LEVEL_COLORS[lv]}"></i></div></div>'
                                       for lv in reversed(LEVELS)) + '</div></div></div>'), unsafe_allow_html=True)
        with g2:
            st.markdown(f'<div class="card"><div class="sec-title">Par référentiel</div>{ui.framework_bars(s["frameworks"])}</div>',
                        unsafe_allow_html=True)
        with g3:
            st.markdown(f'<div class="card"><div class="sec-title">Matrice de risques</div>{ui.heatmap(results)}</div>',
                        unsafe_allow_html=True)
        st.write("")
        d1, d2, d3, _ = st.columns([1, 1, 1, 2])
        d1.download_button("Rapport HTML / PDF", to_html(audit), "rapport_audit_nfc.html", "text/html")
        d2.download_button("Constats CSV", to_csv(audit), "constats_audit_nfc.csv", "text/csv")
        d3.download_button("Données JSON", to_json(audit), "audit_nfc.json", "application/json")
        st.write("")
        ui.section("Constats détaillés", "Classés du plus grave au moins grave.")
        f1, f2, f3 = st.columns([1.3, 1.3, 1])
        levels = f1.multiselect("Niveaux affichés", LEVELS, default=["CRITIQUE", "ELEVE", "MOYEN"],
                                format_func=lambda x: LEVEL_LABELS[x])
        min_score = f2.slider("Score de risque minimum", 1, 25, 1, help="Score = impact × probabilité (de 1 à 25).")
        show_ok = f3.toggle("Afficher les événements conformes", value=False)
        shown = [r for r in sorted(results, key=lambda r: (-r["score"], r["idx"]))
                 if (r["non_conforme"] and r["level"] in levels and r["score"] >= min_score) or (show_ok and not r["non_conforme"])]
        if not shown:
            st.info("Aucun événement ne correspond aux filtres choisis.")
        for r in shown:
            icon = {"CRITIQUE": "🔴", "ELEVE": "🟠", "MOYEN": "🟡", "FAIBLE": "🟢"}[r["level"]]
            with st.expander(f"{icon}  #{r['idx']} · {LEVEL_LABELS[r['level']]} · {r['log']['action']}",
                             expanded=r["level"] == "CRITIQUE" and r["score"] >= 25):
                st.markdown(ui.finding_html(r), unsafe_allow_html=True)

# ----------------------------------------------------------------- Onglet 4 : référentiels
with tab4:
    ui.section("Base de connaissance normative", "Interrogez le moteur de recherche utilisé par l'Agent RAG.")
    q = st.text_input("Rechercher une exigence", placeholder="Ex. compte inactif réactivé sans ticket")
    if q:
        retriever = get_retriever(ss["session_id"], use_embeddings)
        for n in retriever.search(q, k=4):
            st.markdown(ui.H(f'<div class="finding" style="--c:{PALETTE["red"]}"><span class="tag">pertinence {n["score"]:.2f}</span>'
                             f'<b> {ui.e(n["source"])} – {ui.e(n["article"])}</b><div class="meta">{ui.e(n["content"])}</div></div>'),
                        unsafe_allow_html=True)
        if retriever.note:
            st.caption(retriever.note)
    else:
        show_df(pd.DataFrame([{"Référentiel": n["source"], "Article": n["article"], "Exigence": n["content"]} for n in NORMS]))

ui.footer()
