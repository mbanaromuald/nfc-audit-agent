"""Anonymisation PII avant toute transmission au LLM d'inférence.

j.doe@nfcbank.cm -> USER_HASH_8F92 ; 203.0.113.7 -> IP_HASH_41AC.
La table de correspondance reste en mémoire locale pour restituer les noms
réels dans l'interface et le rapport (jamais envoyée au LLM).
"""
from __future__ import annotations

import hashlib
import re
import secrets

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_KEEP = {"", "n/a", "system", "-", "unknown", "inconnue"}


class Anonymizer:
    def __init__(self, salt: str | None = None):
        self.salt = salt or secrets.token_hex(8)
        self.fwd: dict[tuple[str, str], str] = {}
        self.rev: dict[str, str] = {}

    def token(self, value: str, kind: str = "USER") -> str:
        value = str(value).strip()
        if value.lower() in _KEEP:
            return value
        key = (kind, value)
        if key in self.fwd:
            return self.fwd[key]
        n = 4
        while True:
            h = hashlib.sha256(f"{self.salt}|{kind}|{value}".encode()).hexdigest()[:n].upper()
            tok = f"{kind}_HASH_{h}"
            if tok not in self.rev:
                break
            n += 1
        self.fwd[key] = tok
        self.rev[tok] = value
        return tok

    def text(self, text: str) -> str:
        text = str(text)
        text = _EMAIL.sub(lambda m: self.token(m.group(0), "USER"), text)
        text = _IPV4.sub(lambda m: self.token(m.group(0), "IP"), text)
        for (_, value), tok in sorted(self.fwd.items(), key=lambda kv: -len(kv[0][1])):
            text = re.sub(rf"(?<![\w]){re.escape(value)}(?![\w])", tok, text)
        return text

    def restore(self, text: str) -> str:
        text = str(text)
        for tok in sorted(self.rev, key=len, reverse=True):
            text = text.replace(tok, self.rev[tok])
        return text
