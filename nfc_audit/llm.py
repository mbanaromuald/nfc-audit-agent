"""Accès LLM (Groq / Llama 3.3 via LangChain) avec reprise sur limite de débit."""
from __future__ import annotations

import json
import re
import time

from .config import DEFAULT_MODEL


class LLMAuthError(Exception):
    pass


def build_llm(api_key: str, model: str = DEFAULT_MODEL, temperature: float = 0.1):
    from langchain_groq import ChatGroq

    return ChatGroq(model=model, temperature=temperature, api_key=api_key, max_tokens=800, timeout=45)


def invoke_text(llm, prompt: str, retries: int = 3) -> str:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            return str(llm.invoke(prompt).content)
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).lower()
            if "401" in msg or "invalid api key" in msg or "authentication" in msg:
                raise LLMAuthError(str(exc)) from exc
            last = exc
            if "429" in msg or "rate" in msg:
                time.sleep(2 * (attempt + 1))
            else:
                time.sleep(1)
    raise last or RuntimeError("Échec LLM")


def parse_json(text: str) -> dict | None:
    """Extrait le premier objet JSON d'une réponse (tolère les balises ```json)."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
