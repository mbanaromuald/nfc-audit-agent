import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nfc_audit import pipeline
from nfc_audit.anonymizer import Anonymizer
from nfc_audit.ingestion import parse_file, sample_log_text, sample_logs
from nfc_audit.rag import NormRetriever
from nfc_audit.risk import evaluate, level_from_score

APPROVED = {"CHG-2025-089", "CHG-2025-091", "INC-2025-3312", "HR-2025-0412", "REQ-2025-1180"}


def _by_action(results, fragment):
    return next(r for r in results if fragment in r["log"]["action"])


def test_rules_flag_expected_events():
    out = pipeline.run_audit(sample_logs(), NormRetriever(prefer_embeddings=False), use_llm=False, approved_tickets=APPROVED)
    res = out["results"]
    assert _by_action(res, "Création de compte à privilèges")["level"] == "CRITIQUE"
    assert _by_action(res, "ALTER TABLE")["level"] == "CRITIQUE"          # corrélation compte neuf -> prod
    assert _by_action(res, "DROP TABLE")["level"] == "CRITIQUE"
    assert _by_action(res, "Réactivation")["level"] == "ELEVE"
    assert not _by_action(res, "UPDATE PARAMETRES_TAUX")["non_conforme"]  # ticket valide
    assert out["stats"]["total"] == 16


def test_unapproved_ticket_is_flagged():
    out = pipeline.run_audit(sample_logs(), NormRetriever(prefer_embeddings=False), use_llm=False, approved_tickets=set())
    assert _by_action(out["results"], "UPDATE PARAMETRES_TAUX")["non_conforme"]


def test_levels():
    assert [level_from_score(s) for s in (25, 20, 12, 6, 5)] == ["CRITIQUE", "CRITIQUE", "ELEVE", "MOYEN", "FAIBLE"]


def test_anonymizer_roundtrip():
    a = Anonymizer(salt="x")
    t = a.text("j.doe@nfcbank.cm depuis 10.0.0.1")
    assert "nfcbank" not in t and "10.0.0.1" not in t
    assert a.restore(t) == "j.doe@nfcbank.cm depuis 10.0.0.1"


def test_parsers():
    df, _ = parse_file("a.json", json.dumps([{"timestamp": "2025-01-01 10:00:00", "user_id": "u1", "event_type": "login", "status": "ok"}]).encode())
    assert df.loc[0, "actor"] == "u1" and df.loc[0, "action"] == "login"
    df, _ = parse_file("a.log", b'2025-01-01 10:00:00 event_id=4720 user=bob target=eve ticket=N/A')
    assert int(df.loc[0, "event_id"]) == 4720 and df.loc[0, "action"] == "Création de compte"


def test_llm_can_raise_but_not_lower_level(monkeypatch):
    reply = json.dumps({"non_conformite": "Oui", "niveau_risque": "FAIBLE", "normes_violees": [],
                        "justification": "ok", "recommandation": "rien"})
    monkeypatch.setattr(pipeline, "build_llm", lambda *a, **k: object())
    monkeypatch.setattr(pipeline, "invoke_text", lambda llm, p, retries=3: "```json\n" + reply + "\n```")
    out = pipeline.run_audit(sample_logs(), NormRetriever(prefer_embeddings=False), api_key="x", use_llm=True, approved_tickets=APPROVED)
    assert _by_action(out["results"], "DROP TABLE")["level"] == "CRITIQUE"
    assert out["meta"]["llm_events"] > 0


def test_format_is_sniffed_from_content_not_extension():
    demo = sample_logs().head(3)
    as_json = "```json\n" + demo.to_json(orient="records", force_ascii=False) + "\n```"
    as_csv = "```csv\n" + demo.to_csv(index=False) + "```"
    for name, payload in (("gemini-code-1.txt", as_json), ("gemini-code-2.txt", as_csv)):
        df, warns = parse_file(name, payload.encode())
        assert len(df) == 3 and not warns, name


def test_colon_and_syslog_styles_are_understood():
    text = ("[2025-02-15 08:14:22] Event ID: 4720 | User: admin_sys | Target: usr_x | Action: Création de compte | Ticket: N/A\n"
            "Feb 15 08:20:00 DC01 Security: EventID 4728 user=admin_sys target=usr_y ticket=CHG-2025-001")
    df, _ = parse_file("journal.txt", text.encode())
    assert len(df) == 2 and df.loc[0, "actor"] == "admin_sys" and int(df.loc[1, "event_id"]) == 4728


def test_sample_log_roundtrip():
    df, warns = parse_file("exemple.log", sample_log_text().encode())
    assert len(df) == 16 and not warns
    assert df["actor"].tolist() == sample_logs()["actor"].tolist()


def test_code_and_free_text_are_rejected():
    code = "import streamlit as st\nimport pandas as pd\nfrom x import y\ndef main():\n    pass\n"
    df, warns = parse_file("gemini-code-3.txt", code.encode())
    assert df.empty and "code source" in warns[0]
    df, warns = parse_file("notes.txt", "Bonjour,\nnotes de réunion.\nÀ revoir.".encode())
    assert df.empty and "ne ressemble pas à un journal" in warns[0]
