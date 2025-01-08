"""ChromaDB vector store with FAISS fallback."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, persist_dir: str = "./data/chroma"):
        os.makedirs(persist_dir, exist_ok=True)
        self._persist_dir = persist_dir
        self._client = None
        self._collection = None
        self._init_chroma()

    def _init_chroma(self):
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=self._persist_dir)
            self._collection = self._client.get_or_create_collection(
                name="swiftie",
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            logger.warning("ChromaDB init failed (%s), using in-memory fallback", e)
            self._docs: list[tuple[str, str, dict]] = []  # (id, text, meta)

    def add(self, doc_id: str, text: str, metadata: dict | None = None):
        if self._collection is not None:
            try:
                self._collection.upsert(
                    ids=[doc_id], documents=[text], metadatas=[metadata or {}]
                )
                return
            except Exception as e:
                logger.warning("ChromaDB upsert failed: %s", e)
        # fallback
        if hasattr(self, "_docs"):
            self._docs = [(i, t, m) for i, t, m in self._docs if i != doc_id]
            self._docs.append((doc_id, text, metadata or {}))

    def query(self, text: str, n_results: int = 5) -> list[str]:
        if self._collection is not None:
            try:
                if self._collection.count() == 0:
                    return []
                results = self._collection.query(
                    query_texts=[text], n_results=min(n_results, self._collection.count())
                )
                return results["documents"][0] if results["documents"] else []
            except Exception as e:
                logger.warning("ChromaDB query failed: %s", e)
        # fallback: simple keyword match
        if hasattr(self, "_docs"):
            query_words = set(text.lower().split())
            scored = []
            for _, doc_text, _ in self._docs:
                doc_words = set(doc_text.lower().split())
                score = len(query_words & doc_words)
                if score > 0:
                    scored.append((score, doc_text))
            scored.sort(reverse=True)
            return [t for _, t in scored[:n_results]]
        return []

    def count(self) -> int:
        if self._collection is not None:
            try:
                return self._collection.count()
            except Exception:
                pass
        return len(getattr(self, "_docs", []))
