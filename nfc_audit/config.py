"""Configuration centrale : identité de marque, palette, constantes.

La charte est dérivée du logo officiel (assets/logo.png). Pour la modifier, changez
le dictionnaire PALETTE ci-dessous ou remplacez le logo dans assets/.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
DATA = ROOT / "data"

BRAND = {
    "bank": "NFC Bank",
    "bank_long": "National Financial Credit Bank",
    "app": "NFC-AuditAgent",
    "tagline": "We make life easy",
    "developer": "Romuald Arthur MBANA MEDJO",
    "proto": "Prototype de démonstration conçu pour être présenté au jury, en marge de l'entretien de Romuald Arthur MBANA MEDJO.",
    "proto_short": "PROTOTYPE · Présenté au jury en marge de l'entretien · Données fictives",
    "site": "nfcbank.com",
}

# Palette issue du logo officiel : rouge #DB3D42, gris #B6B8B7, graphite #212222.
PALETTE = {
    "ink": "#17181A",       # texte principal
    "graphite": "#212222",  # couleur des lettres du logo
    "red": "#DB3D42",       # rouge NFC Bank (quart de cercle du logo)
    "red_dark": "#A9262C",  # rouge profond (survols, dégradés)
    "gray": "#B6B8B7",      # gris NFC Bank (fond du logo)
    "mist": "#F4F4F4",      # fonds clairs
    "line": "#E1E2E2",      # filets
    "ok": "#1E8E5A",
    "warn": "#D98A0B",
    "high": "#E26F16",
    "crit": "#B3141C",
}

LEVELS = ["FAIBLE", "MOYEN", "ELEVE", "CRITIQUE"]
LEVEL_LABELS = {"FAIBLE": "Faible", "MOYEN": "Moyen", "ELEVE": "Élevé", "CRITIQUE": "Critique"}
LEVEL_COLORS = {
    "FAIBLE": PALETTE["ok"],
    "MOYEN": PALETTE["warn"],
    "ELEVE": PALETTE["high"],
    "CRITIQUE": PALETTE["crit"],
}

DEFAULT_MODEL = "llama-3.3-70b-versatile"
GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
MTTD_TARGET_SECONDS = 300  # objectif : moins de 5 minutes

FRAMEWORKS = [
    ("COBAC", "COBAC R-2016/04"),
    ("ISO", "ISO/IEC 27001:2022"),
    ("COBIT", "COBIT 2019"),
    ("ITIL", "ITIL v4"),
]


def fmt_seconds(seconds: float) -> str:
    """Durée lisible : « < 1 s » pour les exécutions quasi instantanées."""
    return "< 1 s" if seconds < 1 else f"{seconds:g} s"
