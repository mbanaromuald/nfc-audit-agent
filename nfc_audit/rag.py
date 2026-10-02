"""Agent RAG Référentiels : recherche sémantique dans ChromaDB (embeddings locaux MiniLM).

- Embeddings : sentence-transformers/all-MiniLM-L6-v2, exécutés en local.
- Isolation : une collection éphémère en mémoire par session d'audit.
- Repli : si ChromaDB / le modèle d'embeddings est indisponible (premier lancement hors
  ligne, par exemple), une recherche lexicale locale prend le relais sans interrompre l'audit.
"""
from __future__ import annotations

import re
import uuid

from .knowledge import NORMS

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zàâçéèêëîïôûùüÿœ0-9_.-]{3,}", text.lower())}


class NormRetriever:
    def __init__(self, prefer_embeddings: bool = True, session_id: str | None = None):
        self.session_id = session_id or uuid.uuid4().hex[:8]
        self.backend = "lexical"
        self.note = ""
        self._col = None
        if prefer_embeddings:
            try:
                self._init_chroma()
                self.backend = "chromadb + MiniLM-L6-v2 (local)"
            except Exception as exc:  # noqa: BLE001
                self.note = f"Recherche sémantique indisponible ({type(exc).__name__}) : repli lexical local."
                self._col = None
        else:
            self.note = "Recherche lexicale locale (embeddings désactivés)."

    def _init_chroma(self) -> None:
        import chromadb
        from chromadb.utils import embedding_functions

        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
        client = chromadb.Client()
        col = client.get_or_create_collection(name=f"nfc_norms_{self.session_id}", embedding_function=ef)
        col.add(
            ids=[n["id"] for n in NORMS],
            documents=[f"{n['source']} – {n['article']} : {n['content']}" for n in NORMS],
            metadatas=[{"source": n["source"], "article": n["article"], "framework": n["framework"]} for n in NORMS],
        )
        col.query(query_texts=["test"], n_results=1)  # force le chargement du modèle
        self._col = col

    def search(self, query: str, k: int = 3) -> list[dict]:
        by_id = {n["id"]: n for n in NORMS}
        if self._col is not None:
            try:
                res = self._col.query(query_texts=[query], n_results=min(k, len(NORMS)))
                out = []
                for nid, dist in zip(res["ids"][0], res["distances"][0]):
                    n = by_id[nid]
                    out.append({**n, "score": round(1 / (1 + float(dist)), 3)})
                return out
            except Exception as exc:  # noqa: BLE001
                self.note = f"Erreur ChromaDB ({type(exc).__name__}) : repli lexical."
                self._col = None
                self.backend = "lexical"
        q = _tokens(query)
        scored = []
        for n in NORMS:
            doc = _tokens(f"{n['article']} {n['content']} {n['tags']}")
            tags = _tokens(n["tags"])
            overlap = len(q & doc) + 1.5 * len(q & tags)
            scored.append((overlap / (1 + len(q) ** 0.5), n))
        scored.sort(key=lambda x: -x[0])
        top = scored[0][0] or 1.0
        return [{**n, "score": round(s / top, 3)} for s, n in scored[:k]]
