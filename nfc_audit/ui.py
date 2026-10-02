"""Composants visuels – charte dérivée du logo NFC Bank (rouge #DB3D42, gris #B6B8B7, graphite #212222).

Motif signature : le quart de cercle rouge du logo, repris dans le bandeau, les indicateurs et les titres.
"""
from __future__ import annotations

import base64
import html as _html
import mimetypes

import streamlit as st

from .config import ASSETS, BRAND, FRAMEWORKS, LEVEL_COLORS, LEVEL_LABELS, LEVELS, MTTD_TARGET_SECONDS, PALETTE, fmt_seconds

e = _html.escape


def H(s: str) -> str:
    """Compacte un bloc HTML (évite que Markdown le prenne pour du code)."""
    return "\n".join(line.strip() for line in s.strip().splitlines() if line.strip())


def logo_path():
    for name in ("logo.png", "logo.svg", "logo.jpg", "logo.jpeg", "logo.webp", "logo_placeholder.svg"):
        p = ASSETS / name
        if p.exists():
            return p
    return None


def logo_data_uri() -> str:
    p = logo_path()
    if not p:
        return ""
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Figtree:wght@400;500;600;700;800&display=swap');
html,body,.stApp,[class*="css"]{font-family:'Figtree',system-ui,sans-serif}
.stApp{background:radial-gradient(900px 420px at 100% 0,rgba(219,61,66,.07),transparent 60%),linear-gradient(180deg,#ECEDED 0,#F7F7F7 420px,#F7F7F7 100%)}
header[data-testid="stHeader"]{background:transparent}
#MainMenu,footer{visibility:hidden}
.block-container{padding-top:.6rem;padding-bottom:3rem;max-width:1280px}
h1,h2,h3,h4{font-family:'Cormorant Garamond',Georgia,serif;color:var(--ink);letter-spacing:.005em}
section[data-testid="stSidebar"]{background:#fff;border-right:1px solid var(--line)}
:focus-visible{outline:3px solid var(--red)!important;outline-offset:2px}

/* ---------- bandeau prototype ---------- */
.ribbon{display:flex;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap;background:var(--graphite);color:#E9E9E9;
border-radius:12px 12px 0 0;padding:9px 18px;font-size:12.5px;font-weight:600;letter-spacing:.02em;margin-top:6px}
.ribbon b{background:var(--red);color:#fff;border-radius:999px;padding:2px 11px;font-size:11.5px;letter-spacing:.12em}
.ribbon span.dot{width:4px;height:4px;border-radius:50%;background:var(--gray)}

/* ---------- hero ---------- */
.hero-box{container-type:inline-size}
.hero{position:relative;overflow:hidden;border-radius:0 0 26px 26px;min-height:450px;color:var(--graphite);
background:linear-gradient(135deg,#E6E7E7 0,#C9CBCA 55%,var(--gray) 100%);box-shadow:0 30px 60px -34px rgba(33,34,34,.65)}
.hero .qc{position:absolute;left:0;top:0;width:600px;height:100%;border-bottom-right-radius:100%;
background:radial-gradient(120% 120% at 0 0,#EA5A5F 0,var(--red) 45%,var(--red-dark) 100%)}
.hero-grid{position:relative;display:grid;grid-template-columns:600px 1fr;gap:20px;padding:30px 42px 0;min-height:372px}
.h-left{color:#fff;max-width:360px}
.logo-tile{display:inline-flex;background:#fff;border-radius:12px;padding:8px;box-shadow:0 14px 30px -14px rgba(0,0,0,.55)}
.logo-tile img{height:78px;display:block;border-radius:4px}
.hero h1{color:#fff;font-size:52px;line-height:1;margin:18px 0 10px;font-weight:700;letter-spacing:.01em}
.hero p.lead{font-size:15px;line-height:1.55;color:#FFE9EA;margin:0;max-width:330px}
.proto-badge{display:inline-block;margin-left:12px;vertical-align:top;margin-top:6px;border:1.5px solid rgba(255,255,255,.85);color:#fff;
border-radius:999px;padding:5px 14px;font-size:12px;font-weight:800;letter-spacing:.14em}
.h-right{display:flex;align-items:center}
.carousel{position:relative;width:100%;height:270px}
.slide{position:absolute;inset:0 0 34px 0;display:flex;flex-direction:column;justify-content:center;opacity:0;animation:sl 20s infinite both}
.slide h2{font-size:46px;line-height:1.04;margin:0 0 12px;font-weight:700;color:var(--graphite)}
.slide p{font-size:16.5px;line-height:1.6;margin:0;color:#2E3030;max-width:470px}
.slide:nth-child(1){animation-delay:0s}.slide:nth-child(2){animation-delay:5s}
.slide:nth-child(3){animation-delay:10s}.slide:nth-child(4){animation-delay:15s}
@keyframes sl{0%{opacity:0;transform:translateX(28px)}3%{opacity:1;transform:none}22%{opacity:1;transform:none}25%{opacity:0;transform:translateX(-28px)}100%{opacity:0}}
.dots{position:absolute;left:0;bottom:0;display:flex;gap:7px}
.dots i{display:block;height:8px;width:8px;border-radius:99px;background:rgba(33,34,34,.28);animation:dt 20s infinite both}
.dots i:nth-child(2){animation-delay:5s}.dots i:nth-child(3){animation-delay:10s}.dots i:nth-child(4){animation-delay:15s}
@keyframes dt{0%{width:8px;background:rgba(33,34,34,.28)}3%{width:30px;background:var(--red)}22%{width:30px;background:var(--red)}25%{width:8px;background:rgba(33,34,34,.28)}100%{width:8px;background:rgba(33,34,34,.28)}}
.carousel:hover .slide,.carousel:hover .dots i{animation-play-state:paused}
.dev{position:relative;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;padding:14px 42px 16px;margin-top:6px;
border-top:1px solid rgba(33,34,34,.18);font-size:13px;color:#2E3030}
.dev b{color:var(--graphite)} .dev .slogan{font-family:'Cormorant Garamond',serif;font-size:18px;font-style:italic;font-weight:600;color:var(--red-dark)}
@media (prefers-reduced-motion:reduce){.slide,.dots i{animation:none}.slide:nth-child(1){opacity:1}.dots i:nth-child(1){width:30px;background:var(--red)}}
@container (max-width:1020px){
 .hero{min-height:0}.hero .qc{display:none}.hero-grid{grid-template-columns:1fr;padding:22px 20px 0;min-height:0}
 .h-left{max-width:none;background:linear-gradient(135deg,var(--red),var(--red-dark));border-radius:18px;padding:20px}
 .hero h1{font-size:40px}.hero p.lead{max-width:none}.carousel{height:290px}.slide h2{font-size:34px}.dev{padding:14px 20px}}

/* ---------- barre latérale ---------- */
.side-brand{position:relative;overflow:hidden;background:linear-gradient(135deg,#EEEFEF,#D5D6D6);border-radius:16px;padding:16px 16px 14px;margin-bottom:12px;text-align:center}
.side-brand:before{content:"";position:absolute;left:0;top:0;width:78px;height:78px;border-bottom-right-radius:100%;background:var(--red)}
.side-brand .logo-tile{position:relative;padding:6px}.side-brand .logo-tile img{height:62px}
.side-brand small{position:relative;display:block;color:#2E3030;margin-top:10px;font-size:12px;font-weight:600}
.side-proto{background:#FFF1F1;border:1px solid #F4C3C5;border-radius:12px;padding:10px 12px;font-size:12px;color:#7A1A1F;line-height:1.5;margin:10px 0}
.side-dev{font-size:12px;color:#4B4D4D;border-top:1px solid var(--line);padding-top:10px;margin-top:14px;line-height:1.5}
.side-dev b{color:var(--red-dark)}

/* ---------- onglets, boutons, sliders ---------- */
.stTabs [data-baseweb="tab-list"]{gap:6px;background:#fff;padding:6px;border-radius:14px;border:1px solid var(--line);box-shadow:0 8px 22px -16px rgba(33,34,34,.5)}
.stTabs [data-baseweb="tab"]{height:44px;border-radius:10px;padding:0 18px;font-weight:700;color:#4B4D4D}
.stTabs [aria-selected="true"]{background:var(--graphite);color:#fff!important}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none}
.stButton>button,.stDownloadButton>button{border-radius:12px;font-weight:700;padding:.6rem 1.2rem;border:1px solid var(--line)}
.stButton>button[kind="primary"]{background:linear-gradient(135deg,var(--red),var(--red-dark));border:0;color:#fff;box-shadow:0 14px 26px -14px rgba(219,61,66,.9)}
.stButton>button[kind="primary"]:hover{filter:brightness(1.07)}
div[data-baseweb="slider"] [role="slider"]{background-color:var(--red)!important;box-shadow:0 0 0 5px rgba(219,61,66,.18)}
div[data-testid="stSliderThumbValue"]{color:var(--red-dark)!important;font-weight:800}

/* ---------- blocs ---------- */
.sec-title{font-family:'Cormorant Garamond',serif;font-weight:700;font-size:28px;color:var(--ink);margin:8px 0 2px;line-height:1.1}
.sec-title:before{content:"";display:inline-block;width:16px;height:16px;background:var(--red);border-bottom-right-radius:100%;margin-right:10px;vertical-align:2px}
.sec-sub{color:#4B4D4D;font-size:14.5px;margin:0 0 14px 26px}
.card{background:#fff;border:1px solid var(--line);border-radius:18px;padding:20px 22px;box-shadow:0 16px 36px -28px rgba(33,34,34,.6)}
.card .sec-title{font-size:22px}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:6px 0 18px}
.kpi{background:#fff;border:1px solid var(--line);border-radius:18px;padding:20px 20px 16px 20px;position:relative;overflow:hidden}
.kpi:before{content:"";position:absolute;left:0;top:0;width:46px;height:46px;border-bottom-right-radius:100%;background:var(--c,var(--red))}
.kpi .v{font-family:'Cormorant Garamond',serif;font-size:52px;font-weight:700;color:var(--ink);line-height:1;margin-top:24px;font-variant-numeric:lining-nums}
.kpi .l{font-size:13.5px;color:var(--graphite);font-weight:700;margin-top:6px}
.kpi .s{font-size:12px;color:#6A6C6C;margin-top:4px}
@media (max-width:900px){.kpis{grid-template-columns:repeat(2,1fr)}}

.agents{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.agent{background:#fff;border:1px solid var(--line);border-radius:18px;padding:18px;position:relative}
.agent .ic{width:44px;height:44px;border-radius:12px 12px 12px 0;background:linear-gradient(135deg,var(--red),var(--red-dark));color:#fff;display:flex;align-items:center;justify-content:center;font-size:20px;margin-bottom:10px}
.agent h4{margin:0 0 4px;font-size:21px}.agent p{margin:0;color:#4B4D4D;font-size:13px;line-height:1.5}
.agent.done{border-color:var(--ok)}.agent.done:after{content:"✓";position:absolute;top:12px;right:14px;color:var(--ok);font-weight:800}
@media (max-width:900px){.agents{grid-template-columns:repeat(2,1fr)}}

.pitch{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.pitch .card h4{font-size:24px;margin:0 0 6px}.pitch .card p{margin:0;font-size:14px;line-height:1.6;color:#3A3C3C}
@media (max-width:900px){.pitch{grid-template-columns:1fr}}
.road{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:6px}
.road div{border-top:4px solid var(--red);background:#fff;border-radius:0 0 14px 14px;padding:12px 14px;font-size:13.5px;line-height:1.5;border-left:1px solid var(--line);border-right:1px solid var(--line);border-bottom:1px solid var(--line)}
.road b{display:block;font-family:'Cormorant Garamond',serif;font-size:20px;margin-bottom:2px}
@media (max-width:900px){.road{grid-template-columns:1fr 1fr}}

.gauge-wrap{display:flex;align-items:center;gap:22px}
.gauge{--p:0;--c:var(--ok);width:150px;height:150px;border-radius:50%;flex:none;background:conic-gradient(var(--c) calc(var(--p)*1%),#E6E7E7 0);display:flex;align-items:center;justify-content:center}
.gauge i{font-style:normal;width:112px;height:112px;border-radius:50%;background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center}
.gauge i b{font-family:'Cormorant Garamond',serif;font-size:36px;color:var(--ink);line-height:1}.gauge i span{font-size:11px;color:#6A6C6C}
.bar{margin:9px 0}.bar .t{display:flex;justify-content:space-between;font-size:13px;font-weight:600;color:var(--graphite);margin-bottom:4px}
.bar .tr{height:9px;border-radius:99px;background:#E6E7E7;overflow:hidden}.bar .tr i{display:block;height:100%;border-radius:99px;background:var(--c)}
.heat{display:grid;grid-template-columns:30px repeat(5,1fr);gap:4px;font-size:12px}
.heat .c{height:42px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:16px}
.heat .ax{display:flex;align-items:center;justify-content:center;color:#6A6C6C;font-weight:600}
.heat-cap{display:flex;justify-content:space-between;font-size:12px;color:#6A6C6C;margin-top:6px;padding-left:30px}

.pill{display:inline-block;border-radius:999px;padding:3px 12px;font-size:12px;font-weight:800;color:#fff;background:var(--c)}
.finding{border:1px solid var(--line);border-left:6px solid var(--c);border-radius:14px;padding:16px 18px;background:#fff;margin-bottom:6px}
.finding .meta{font-size:13px;color:#4B4D4D;margin:6px 0 10px;line-height:1.6}
.finding code{background:var(--mist);padding:1px 6px;border-radius:6px;color:var(--red-dark)}
.finding .lbl{font-weight:700;color:var(--ink)}
.tag{display:inline-block;background:var(--mist);border:1px solid var(--line);color:var(--graphite);border-radius:8px;padding:2px 9px;font-size:12px;font-weight:600;margin:2px 4px 2px 0}
.note{background:#FFF4E5;border:1px solid #F2D3A3;border-radius:12px;padding:10px 14px;font-size:13px;color:#6B4300}
.summary{background:#fff;border:1px solid var(--line);border-left:6px solid var(--red);border-radius:16px;padding:18px 22px;font-size:15.5px;line-height:1.7}
.sim{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:8px}
.sim .big{font-family:'Cormorant Garamond',serif;font-size:64px;font-weight:700;line-height:1;color:var(--red-dark)}
.sim .cap{font-size:13px;color:#4B4D4D;margin-top:6px}
@media (max-width:900px){.sim{grid-template-columns:1fr}}
.foot{margin-top:34px;text-align:center;color:#4B4D4D;font-size:13px;line-height:1.7}
.foot b{color:var(--red-dark)}
"""


def inject_css() -> None:
    root = ":root{" + ";".join(f"--{k.replace('_', '-')}:{v}" for k, v in PALETTE.items()) + "}"
    st.markdown(f"<style>{root}{CSS}</style>", unsafe_allow_html=True)


SLIDES = [
    ("Votre audit ne dort jamais.",
     "Chaque journal Active Directory et chaque base de production est contrôlé en continu, pas une fois par trimestre."),
    ("Une anomalie. Quatre référentiels.",
     "COBAC, ISO 27001, COBIT 2019 et ITIL v4 rapprochés en un seul constat, article par article."),
    ("Des secondes, pas des semaines.",
     "Sur le jeu de démonstration, l'audit complet se mesure en secondes. Le chronomètre s'affiche dans le rapport."),
    ("Vos identités restent masquées.",
     "Pseudonymisation avant toute analyse IA, et un mode hors ligne où aucune donnée ne quitte votre réseau."),
]


def proto_ribbon() -> None:
    st.markdown(H(f"""<div class="ribbon"><b>PROTOTYPE</b><span>Présenté au jury en marge de l'entretien</span>
    <span class="dot"></span><span>Données fictives</span><span class="dot"></span><span>{e(BRAND['developer'])}</span></div>"""),
                unsafe_allow_html=True)


def hero() -> None:
    slides = "".join(f'<div class="slide"><h2>{e(t)}</h2><p>{e(d)}</p></div>' for t, d in SLIDES)
    st.markdown(H(f"""
    <div class="hero-box"><div class="hero"><div class="qc"></div>
    <div class="hero-grid">
      <div class="h-left">
        <div class="logo-tile"><img src="{logo_data_uri()}" alt="Logo {e(BRAND['bank'])}"></div>
        <span class="proto-badge">PROTOTYPE</span>
        <h1>{e(BRAND['app'])}</h1>
        <p class="lead">L'agent qui lit vos journaux, les confronte à la réglementation et rend au Comité d'Audit des constats prêts à décider.</p>
      </div>
      <div class="h-right"><div class="carousel">{slides}<div class="dots"><i></i><i></i><i></i><i></i></div></div></div>
    </div>
    <div class="dev"><span>Conçu et développé par <b>{e(BRAND['developer'])}</b> · Prototype présenté au jury en marge de l'entretien</span>
    <span class="slogan">{e(BRAND['bank'])} · {e(BRAND['tagline'])}</span></div></div></div>"""), unsafe_allow_html=True)


def sidebar_brand() -> None:
    st.sidebar.markdown(H(f"""
    <div class="side-brand"><div class="logo-tile"><img src="{logo_data_uri()}" alt="Logo {e(BRAND['bank'])}"></div>
    <small>{e(BRAND['app'])} · Audit et conformité SI</small></div>
    <div class="side-proto"><b>Prototype</b> présenté au jury en marge de l'entretien. Les données affichées sont fictives.</div>"""),
                        unsafe_allow_html=True)


def sidebar_footer() -> None:
    st.sidebar.markdown(H(f"""
    <div class="side-dev">Développeur<br><b>{e(BRAND['developer'])}</b><br>{e(BRAND['bank_long'])}</div>"""),
                        unsafe_allow_html=True)


def footer() -> None:
    st.markdown(H(f"""
    <div class="foot">{e(BRAND['app'])} · {e(BRAND['bank_long'])}<br>
    <b>Prototype</b> présenté au jury en marge de l'entretien de <b>{e(BRAND['developer'])}</b> · Données fictives, non contractuel</div>"""),
                unsafe_allow_html=True)


def section(title: str, sub: str = "") -> None:
    st.markdown(H(f'<div class="sec-title">{e(title)}</div><div class="sec-sub">{e(sub)}</div>'), unsafe_allow_html=True)


def kpis(items: list[tuple[str, str, str, str]]) -> None:
    cards = "".join(
        f'<div class="kpi" style="--c:{c}"><div class="v">{e(v)}</div><div class="l">{e(l)}</div><div class="s">{e(s)}</div></div>'
        for l, v, s, c in items)
    st.markdown(f'<div class="kpis">{cards}</div>', unsafe_allow_html=True)


def agents_cards(done: bool = False) -> None:
    data = [("📥", "Agent Ingestion", "Lit les fichiers .json, .csv, .log, normalise et pseudonymise les identités."),
            ("📚", "Agent RAG", "Retrouve dans ChromaDB les articles applicables, avec des embeddings locaux."),
            ("⚖️", "Agent Évaluation", "Applique les règles, corrèle les événements et calcule impact × probabilité."),
            ("📝", "Agent Reporting", "Rédige la synthèse, les constats et les plans d'action pour le Comité.")]
    cls = "agent done" if done else "agent"
    st.markdown('<div class="agents">' + "".join(
        f'<div class="{cls}"><div class="ic">{i}</div><h4>{e(t)}</h4><p>{e(d)}</p></div>' for i, t, d in data) + "</div>",
                unsafe_allow_html=True)


def pitch_cards() -> None:
    items = [("Détecter ce qu'un œil humain rate",
              "Un compte créé sans ticket qui modifie la base de production quelques minutes plus tard : l'agent relie les deux événements, là où une revue manuelle les voit séparément."),
             ("Prouver, article par article",
              "Chaque écart est rattaché aux exigences COBAC, ISO 27001:2022, COBIT 2019 et ITIL v4 concernées, avec le plan d'action associé et un export pour le Comité."),
             ("Garder la main sur les données",
              "Embeddings calculés en local, identités pseudonymisées avant l'IA, mode hors ligne complet. L'IA relève un risque, elle ne peut jamais le minimiser.")]
    st.markdown('<div class="pitch">' + "".join(f'<div class="card"><h4>{e(t)}</h4><p>{e(d)}</p></div>' for t, d in items) + "</div>",
                unsafe_allow_html=True)


def roadmap() -> None:
    steps = [("Connecteurs", "Lecture directe des journaux AD, Oracle et du SIEM, sans export manuel."),
             ("Identité & droits", "Authentification SSO, rôles auditeur / RSSI, journal d'accès à l'outil."),
             ("Données & sécurité", "Stockage chiffré, rétention maîtrisée, hébergement interne ou souverain."),
             ("Validation réglementaire", "Revue des textes COBAC et des règles par la Conformité avant production.")]
    st.markdown('<div class="road">' + "".join(f"<div><b>{e(t)}</b>{e(d)}</div>" for t, d in steps) + "</div>", unsafe_allow_html=True)


def simulator(manual_h: float, agent_h: float) -> str:
    saved = max(manual_h - agent_h, 0)
    pct_manual, pct_agent = 100, round(100 * agent_h / manual_h) if manual_h else 0
    return H(f"""
    <div class="sim"><div class="card"><div class="big">{saved:,.0f} h</div>
    <div class="cap">de travail d'audit libérées chaque semaine, soit environ <b>{saved * 46:,.0f} h par an</b>.</div></div>
    <div class="card">
      <div class="bar"><div class="t"><span>Contrôle manuel</span><span>{manual_h:,.0f} h / semaine</span></div><div class="tr"><i style="width:{pct_manual}%;--c:var(--gray)"></i></div></div>
      <div class="bar"><div class="t"><span>Avec NFC-AuditAgent (validation des écarts)</span><span>{agent_h:,.0f} h / semaine</span></div><div class="tr"><i style="width:{pct_agent}%;--c:var(--red)"></i></div></div>
      <div class="cap">Simulation illustrative fondée sur vos hypothèses, non mesurée en production.</div>
    </div></div>""".replace(",", " "))


def gauge(pct: float) -> str:
    color = PALETTE["ok"] if pct >= 85 else PALETTE["warn"] if pct >= 60 else PALETTE["crit"]
    return f'<div class="gauge" style="--p:{pct};--c:{color}"><i><b>{pct:g}%</b><span>conformité</span></i></div>'


def framework_bars(scores: dict[str, float]) -> str:
    out = []
    for key, label in FRAMEWORKS:
        v = scores.get(key, 100)
        color = PALETTE["ok"] if v >= 85 else PALETTE["warn"] if v >= 60 else PALETTE["crit"]
        out.append(f'<div class="bar"><div class="t"><span>{e(label)}</span><span>{v:g}%</span></div>'
                   f'<div class="tr"><i style="width:{v}%;--c:{color}"></i></div></div>')
    return "".join(out)


def heatmap(results: list[dict]) -> str:
    counts: dict[tuple[int, int], int] = {}
    for r in results:
        if r["non_conforme"]:
            counts[(r["impact"], r["probability"])] = counts.get((r["impact"], r["probability"]), 0) + 1
    cells = []
    for imp in range(5, 0, -1):
        cells.append(f'<div class="ax">{imp}</div>')
        for prob in range(1, 6):
            sc = imp * prob
            key = "CRITIQUE" if sc >= 20 else "ELEVE" if sc >= 12 else "MOYEN" if sc >= 6 else "FAIBLE"
            n = counts.get((imp, prob), 0)
            bg = LEVEL_COLORS[key]
            style = f"background:{bg};color:#fff" if n else f"background:{bg};opacity:.15"
            cells.append(f'<div class="c" style="{style}">{n if n else ""}</div>')
    return ('<div class="heat">' + "".join(cells) + '<div></div>' +
            "".join(f'<div class="ax">{p}</div>' for p in range(1, 6)) +
            '</div><div class="heat-cap"><span>Probabilité →</span><span>Impact ↑</span></div>')


def pill(level: str) -> str:
    return f'<span class="pill" style="--c:{LEVEL_COLORS[level]}">{e(LEVEL_LABELS[level])}</span>'


def finding_html(r: dict) -> str:
    log = r["log"]
    norms = "".join(f'<span class="tag">{e(n["source"])} · {e(n["article"].split(" – ")[0])}</span>' for n in r["norms"]) \
        or '<span class="tag">Aucune exigence enfreinte</span>'
    refs = "".join(f'<span class="tag">{e(n["id"])} ({n["score"]:.2f})</span>' for n in r["retrieved"])
    eid = log["event_id"] if log["event_id"] != "" else "—"
    return H(f"""
    <div class="finding" style="--c:{LEVEL_COLORS[r['level']]}">
      {pill(r['level'])} <span class="tag">Score {r['score']} (impact {r['impact']} × probabilité {r['probability']})</span>
      <span class="tag">{e(r['mode'])}</span>
      <div class="meta">{e(log['timestamp'])} · {e(log['source_sys'])} · Event ID {e(str(eid))}<br>
      Acteur <code>{e(log['actor'])}</code> → cible <code>{e(log['user_target'])}</code> · Ticket <code>{e(log['ticket_ref'])}</code>
      · IP <code>{e(log['ip_address'] or '—')}</code></div>
      <div><span class="lbl">Constat :</span> {e(r['justification'])}</div>
      <div style="margin-top:8px"><span class="lbl">Plan d'action :</span> {e(r['recommendation'])}</div>
      <div style="margin-top:10px"><span class="lbl">Exigences enfreintes :</span><br>{norms}</div>
      <div style="margin-top:6px"><span class="lbl">Références consultées (RAG) :</span><br>{refs}</div>
    </div>""")


def mttd_card(elapsed_s: float) -> tuple[str, str, str, str]:
    ok = elapsed_s <= MTTD_TARGET_SECONDS
    return ("Délai d'analyse", fmt_seconds(elapsed_s), "Objectif : moins de 300 s" + (" · atteint" if ok else " · dépassé"),
            PALETTE["ok"] if ok else PALETTE["crit"])
