"""Agent Ingestion & Parsing : lecture et normalisation des journaux (.json, .csv, .log)."""
from __future__ import annotations

import io
import json
import re
from datetime import datetime

import pandas as pd

CANON = ["timestamp", "source_sys", "event_id", "user_target", "actor", "action",
         "resource", "status", "ip_address", "ticket_ref"]

ALIASES = {
    "timestamp": ["timestamp", "time", "date", "datetime", "@timestamp", "event_time", "timecreated", "created"],
    "source_sys": ["source_sys", "source", "system", "log_source", "provider", "sys"],
    "event_id": ["event_id", "eventid", "event_code", "eid", "id"],
    "user_target": ["user_target", "target", "target_user", "targetusername", "cible", "target_account"],
    "actor": ["actor", "user_id", "user", "username", "subject", "subjectusername", "acteur", "performed_by"],
    "action": ["action", "event_type", "message", "description", "operation", "statement", "sql", "event"],
    "resource": ["resource", "object", "table", "ressource", "path", "target_resource"],
    "status": ["status", "result", "outcome", "statut"],
    "ip_address": ["ip_address", "ip", "src_ip", "source_ip", "client_ip", "ipaddress"],
    "ticket_ref": ["ticket_ref", "ticket", "change_id", "rfc", "itsm_ref", "jira", "ticket_id"],
}

EVENT_LABELS = {
    4624: "Ouverture de session réussie",
    4625: "Échec d'ouverture de session",
    4720: "Création de compte",
    4722: "Activation de compte",
    4724: "Réinitialisation de mot de passe",
    4725: "Désactivation de compte",
    4726: "Suppression de compte",
    4728: "Ajout à un groupe global de sécurité",
    4732: "Ajout à un groupe local de sécurité",
    4738: "Modification de compte",
    4740: "Verrouillage de compte",
    4756: "Ajout à un groupe universel de sécurité",
}

_KV = re.compile(r'([A-Za-z_]\w*)=("[^"]*"|\S+)')
_FENCE = re.compile(r"^\s*```[\w-]*\s*$", re.M)
_ISO = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}")
_FR = re.compile(r"(\d{2})/(\d{2})/(\d{4})[ T](\d{2}:\d{2}:\d{2})")
_SYSLOG = re.compile(r"\b([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d{2}:\d{2}:\d{2})\b")
_EVID = re.compile(r"event\s*_?\s*id\D{0,4}(\d{3,5})", re.I)
_CODE_LINE = re.compile(r"^\s*(import |from \w+ import |def |class |function |const |let |var |#include|public |package )")
_MONTHS = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
KNOWN_COLUMNS = {a for aliases in ALIASES.values() for a in aliases}


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    out = pd.DataFrame(index=df.index)
    used: set[str] = set()
    for canon in CANON:
        src = next((a for a in ALIASES[canon] if a in df.columns and a not in used), None)
        if src is not None:
            used.add(src)
            out[canon] = df[src]
        else:
            out[canon] = None
    out["event_id"] = pd.to_numeric(out["event_id"], errors="coerce").astype("Int64")
    for col in ["source_sys", "user_target", "actor", "action", "resource", "status", "ip_address", "ticket_ref"]:
        out[col] = out[col].astype("object").where(out[col].notna(), "").astype(str).str.strip()
        out.loc[out[col].str.lower().isin(["nan", "none", "null"]), col] = ""
    # Libellé d'action déduit de l'Event ID AD si absent
    for i, row in out.iterrows():
        if not row["action"] and pd.notna(row["event_id"]):
            out.at[i, "action"] = EVENT_LABELS.get(int(row["event_id"]), f"Événement {int(row['event_id'])}")
    out["source_sys"] = out["source_sys"].replace("", "Inconnue")
    out["ticket_ref"] = out["ticket_ref"].replace("", "N/A")
    out["timestamp"] = out["timestamp"].astype(str).replace({"None": "", "nan": ""})
    return out


def _extract_timestamp(line: str) -> tuple[str, str]:
    """Trouve un horodatage ISO, jj/mm/aaaa ou syslog dans la ligne ; retourne (horodatage, ligne sans horodatage)."""
    m = _ISO.search(line)
    if m:
        return m.group(0).replace("T", " "), line[:m.start()] + " " + line[m.end():]
    m = _FR.search(line)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)} {m.group(4)}", line[:m.start()] + " " + line[m.end():]
    m = _SYSLOG.search(line)
    if m and m.group(1) in _MONTHS:
        ts = f"{datetime.now().year}-{_MONTHS[m.group(1)]:02d}-{int(m.group(2)):02d} {m.group(3)}"
        return ts, line[:m.start()] + " " + line[m.end():]
    return "", line


def _line_pairs(rest: str) -> dict[str, str]:
    """Extrait les paires « clé=valeur » et « Clé: valeur » (séparées par | ; ou virgule)."""
    pairs = {k.lower(): v.strip('"') for k, v in _KV.findall(rest)}
    for seg in re.split(r"\s*[|;]\s*|\s{2,}|,\s(?=[A-Za-z_ ]{2,25}:)", rest):
        head, sep, value = seg.partition(":")
        if sep and "=" not in head:
            key = re.sub(r"[^\w]+", "_", head.strip().lower()).strip("_")
            if key and len(key) <= 30 and key.count("_") <= 2 and value.strip():
                pairs.setdefault(key, value.strip().strip('"'))
    return pairs


def _parse_log_text(text: str) -> pd.DataFrame:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("{"):
            try:
                rows.append(json.loads(line))
                continue
            except json.JSONDecodeError:
                pass
        ts, rest = _extract_timestamp(line)
        row: dict = _line_pairs(rest)
        if ts and "timestamp" not in row:
            row["timestamp"] = ts
        if not any(k in row for k in ("event_id", "eventid", "eid")):
            m = _EVID.search(line)
            if m:
                row["event_id"] = m.group(1)
        rows.append(row if len(row) > 0 else {"action": line})
    return pd.DataFrame(rows)


def _sniff(text: str, name: str) -> str:
    """Devine le format d'après le contenu (et non l'extension) : json, csv:<sep> ou log."""
    s = text.lstrip()
    if s.startswith("[") or s.startswith("{"):
        return "json"
    first = next((ln for ln in text.splitlines() if ln.strip()), "")
    for sep in (",", ";", "\t", "|"):
        cells = [c.strip().strip('"').lower() for c in first.split(sep)]
        if len(cells) >= 3 and sum(c in KNOWN_COLUMNS for c in cells) >= 2:
            return "csv:" + sep
    lower = name.lower()
    if lower.endswith(".json"):
        return "json"
    if lower.endswith(".csv"):
        return "csv:auto"
    return "log"


def _looks_like_code(text: str) -> bool:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return sum(1 for ln in lines if _CODE_LINE.match(ln)) >= 3


NOT_A_LOG = ("{name} : ce fichier ne ressemble pas à un journal d'événements (ni horodatage, ni acteur, ni Event ID reconnus){code}. "
             "Importez un export .json, .csv ou .log — un fichier d'exemple est téléchargeable juste en dessous.")


def parse_file(name: str, content: bytes) -> tuple[pd.DataFrame, list[str]]:
    """Retourne (DataFrame normalisé, avertissements). Le format est deviné d'après le contenu."""
    warnings: list[str] = []
    text = content.decode("utf-8-sig", errors="replace")
    text = _FENCE.sub("", text)  # tolère les blocs ```json / ```csv copiés depuis un assistant ou un forum
    if not text.strip():
        return pd.DataFrame(columns=CANON), [f"{name} : fichier vide"]
    kind = _sniff(text, name)
    try:
        if kind == "json":
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    data = next((v for v in data.values() if isinstance(v, list)), [data])
                raw = pd.DataFrame(data)
            except json.JSONDecodeError:
                raw = _parse_log_text(text)  # JSON lignes par lignes
        elif kind.startswith("csv"):
            head = text.splitlines()[0]
            sep = kind.split(":", 1)[1]
            if sep == "auto":
                sep = ";" if head.count(";") > head.count(",") else ","
            raw = pd.read_csv(io.StringIO(text), sep=sep)
        else:
            raw = _parse_log_text(text)
    except Exception as exc:  # noqa: BLE001
        return pd.DataFrame(columns=CANON), [f"{name} : lecture impossible ({exc})"]
    if raw.empty:
        return pd.DataFrame(columns=CANON), [f"{name} : aucun événement détecté"]
    df = _normalize(raw)
    ts_ok = pd.to_datetime(df["timestamp"], errors="coerce").notna().mean()
    who_ok = ((df["actor"] != "") | (df["user_target"] != "")).mean()
    id_ok = df["event_id"].notna().mean()
    if ts_ok < 0.3 and who_ok < 0.3 and id_ok < 0.3:
        code = " ; il s'agit plutôt de code source" if _looks_like_code(text) else ""
        return pd.DataFrame(columns=CANON), [NOT_A_LOG.format(name=name, code=code)]
    if ts_ok < 0.3:
        warnings.append(f"{name} : horodatages absents ou illisibles, la corrélation temporelle sera limitée")
    if who_ok < 0.3:
        warnings.append(f"{name} : colonne acteur introuvable (user_id, actor, user…)")
    return df, warnings


def load_files(files: list[tuple[str, bytes]]) -> tuple[pd.DataFrame, list[str]]:
    frames, warnings = [], []
    for name, content in files:
        df, w = parse_file(name, content)
        warnings += w
        if not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame(columns=CANON), warnings
    full = pd.concat(frames, ignore_index=True)
    ts = pd.to_datetime(full["timestamp"], errors="coerce")
    full = full.assign(_ts=ts).sort_values("_ts", kind="stable", na_position="last").drop(columns="_ts")
    return full.reset_index(drop=True), warnings


def load_itsm_tickets(content: bytes) -> set[str]:
    """CSV ITSM optionnel : colonnes ticket_ref + status. Retourne les tickets approuvés."""
    df = pd.read_csv(io.BytesIO(content))
    df.columns = [c.strip().lower() for c in df.columns]
    ref = next((c for c in ALIASES["ticket_ref"] + ["key", "number"] if c in df.columns), None)
    if ref is None:
        raise ValueError("colonne ticket_ref introuvable")
    st_col = next((c for c in ("status", "statut", "state") if c in df.columns), None)
    approved_words = ("appro", "clos", "closed", "done", "résolu", "resolu", "implement", "terminé", "termine")
    if st_col is None:
        return {str(x).strip() for x in df[ref]}
    ok = df[st_col].astype(str).str.lower().apply(lambda s: any(w in s for w in approved_words))
    return {str(x).strip() for x in df.loc[ok, ref]}


def sample_logs() -> pd.DataFrame:
    """Jeu de démonstration (journaux AD / Oracle) incluant des cas conformes et non conformes."""
    d = "2025-02-17"
    rows = [
        (f"{d} 08:14:22", "Active Directory", 4720, "usr_consultant_ext", "admin_sys", "Création de compte à privilèges", "OU=Prestataires", "Success", "10.20.4.12", "N/A"),
        (f"{d} 08:30:00", "Oracle DB Prod", 1014, "SYSTEM", "usr_consultant_ext", "ALTER TABLE CLIENT_BALANCE_NFC", "CLIENT_BALANCE_NFC", "Success", "10.20.8.45", "CHG-2025-089"),
        (f"{d} 09:05:11", "Active Directory", 4738, "usr_ex_employee", "admin_sys", "Réactivation de compte inactif (>90j)", "OU=Anciens", "Success", "10.20.4.12", "N/A"),
        (f"{d} 09:40:03", "Active Directory", 4724, "usr_k.nana", "helpdesk_01", "Réinitialisation de mot de passe", "OU=Agences", "Success", "10.20.3.8", "INC-2025-3312"),
        (f"{d} 10:12:47", "Active Directory", 4728, "usr_dba_02", "usr_dba_02", "Ajout au groupe DBA_PROD (compte à privilèges)", "CN=DBA_PROD", "Success", "10.20.8.51", "N/A"),
        (f"{d} 10:58:30", "Oracle DB Prod", 1020, "SYSTEM", "usr_dba_01", "UPDATE PARAMETRES_TAUX SET TAUX = 4.5", "PARAMETRES_TAUX", "Success", "10.20.8.40", "CHG-2025-091"),
        (f"{d} 11:20:15", "Active Directory", 4725, "usr_dep_2024", "hr_bot", "Désactivation de compte (départ)", "OU=Departs", "Success", "10.20.2.5", "HR-2025-0412"),
        (f"{d} 13:02:09", "Active Directory", 4720, "usr_stagiaire_07", "helpdesk_02", "Création de compte standard", "OU=Stagiaires", "Success", "10.20.3.9", "REQ-2025-1180"),
        (f"{d} 14:15:00", "Oracle DB Prod", 1014, "SYSTEM", "usr_dba_03", "DROP TABLE TMP_EXPORT_CLIENTS", "TMP_EXPORT_CLIENTS", "Success", "10.20.8.52", "N/A"),
        (f"{d} 22:47:31", "Active Directory", 4728, "usr_support_n2", "admin_sys", "Ajout au groupe Administrateurs locaux", "CN=Administrateurs", "Success", "10.20.4.12", "chg-urgent"),
    ]
    for k in range(5):
        rows.append((f"{d} 03:12:{10 + k * 7:02d}", "Active Directory", 4625, "usr_dg_office", "usr_dg_office",
                     "Échec d'ouverture de session", "VPN-GW-01", "Failure", "203.0.113.77", "N/A"))
    rows.append((f"{d} 03:14:02", "Active Directory", 4624, "usr_dg_office", "usr_dg_office",
                 "Ouverture de session réussie", "VPN-GW-01", "Success", "203.0.113.77", "N/A"))
    cols = ["timestamp", "source_sys", "event_id", "user_target", "actor", "action", "resource", "status", "ip_address", "ticket_ref"]
    df = pd.DataFrame(rows, columns=cols)
    df["event_id"] = df["event_id"].astype("Int64")
    return df.sort_values("timestamp", kind="stable").reset_index(drop=True)


def sample_itsm_csv() -> str:
    return ("ticket_ref,status,summary\n"
            "CHG-2025-089,Approuvé,Maintenance planifiée table soldes\n"
            "CHG-2025-091,Approuvé,Mise à jour du taux directeur\n"
            "INC-2025-3312,Clôturé,Mot de passe oublié agence\n"
            "HR-2025-0412,Clôturé,Départ collaborateur\n"
            "REQ-2025-1180,Approuvé,Compte stagiaire\n")


def sample_log_text() -> str:
    """Le jeu de démonstration au format texte « clé=valeur » (un événement par ligne)."""
    lines = []
    for _, r in sample_logs().iterrows():
        lines.append(f'{r["timestamp"]} source="{r["source_sys"]}" event_id={r["event_id"]} user={r["actor"]} '
                     f'target={r["user_target"]} action="{r["action"]}" resource="{r["resource"]}" '
                     f'status={r["status"]} ip={r["ip_address"]} ticket={r["ticket_ref"]}')
    return "\n".join(lines) + "\n"
