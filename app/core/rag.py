"""RAG pipeline - hybrid BM25 + vector search with reranking."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


@dataclass
class RetrievedDoc:
    text: str
    score: float
    source: str = ""  # "vector" | "bm25" | "fused"
    metadata: dict | None = None


class RAGPipeline:
    """Retrieval augmented generation with hybrid search and reranking."""

    def __init__(
        self,
        vectorstore,
        bm25_weight: float = 0.4,
        vector_weight: float = 0.6,
        max_docs: int = 5,
        reranker=None,
    ):
        self.vectorstore = vectorstore
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
        self.max_docs = max_docs
        self.reranker = reranker
        self._corpus: list[str] = []
        self._bm25: BM25Okapi | None = None

    def _rebuild_bm25(self):
        """Rebuild BM25 index from corpus."""
        if not self._corpus:
            self._bm25 = None
            return
        tokenized = [doc.lower().split() for doc in self._corpus]
        self._bm25 = BM25Okapi(tokenized)

    def add_document(self, doc_id: str, text: str, metadata: dict | None = None):
        self.vectorstore.add(doc_id, text, metadata)
        self._corpus.append(text)
        self._rebuild_bm25()

    def _bm25_search(self, query: str, n: int) -> list[RetrievedDoc]:
        if not self._bm25 or not self._corpus:
            return []
        tokenized_query = query.lower().split()
        scores = self._bm25.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:n]
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append(
                    RetrievedDoc(text=self._corpus[idx], score=float(scores[idx]), source="bm25")
                )
        return results

    def _vector_search(self, query: str, n: int) -> list[RetrievedDoc]:
        docs = self.vectorstore.query(query, n_results=n)
        return [RetrievedDoc(text=d, score=1.0 / (i + 1), source="vector") for i, d in enumerate(docs)]

    def retrieve(self, query: str, n: int | None = None) -> list[RetrievedDoc]:
        """Hybrid retrieval with reciprocal rank fusion."""
        n = n or self.max_docs
        fetch_n = n * 3  # overfetch for fusion

        vector_results = self._vector_search(query, fetch_n)
        bm25_results = self._bm25_search(query, fetch_n)

        # reciprocal rank fusion
        k = 60  # RRF constant
        doc_scores: dict[str, float] = {}
        doc_map: dict[str, RetrievedDoc] = {}

        for rank, doc in enumerate(vector_results):
            rrf = self.vector_weight / (k + rank + 1)
            doc_scores[doc.text] = doc_scores.get(doc.text, 0) + rrf
            doc_map[doc.text] = doc

        for rank, doc in enumerate(bm25_results):
            rrf = self.bm25_weight / (k + rank + 1)
            doc_scores[doc.text] = doc_scores.get(doc.text, 0) + rrf
            if doc.text not in doc_map:
                doc_map[doc.text] = doc

        # sort by fused score
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        fused = []
        for text, score in sorted_docs[:n * 2]:
            doc = doc_map[text]
            fused.append(RetrievedDoc(text=text, score=score, source="fused", metadata=doc.metadata))

        # rerank if available
        if self.reranker and fused:
            fused = self._rerank(query, fused, n)
        else:
            fused = fused[:n]

        return fused

    def _rerank(self, query: str, docs: list[RetrievedDoc], n: int) -> list[RetrievedDoc]:
        """Rerank using cross-encoder."""
        try:
            pairs = [(query, d.text) for d in docs]
            scores = self.reranker.predict(pairs)
            for doc, score in zip(docs, scores):
                doc.score = float(score)
            docs.sort(key=lambda d: d.score, reverse=True)
            return docs[:n]
        except Exception as e:
            logger.warning("Reranking failed: %s", e)
            return docs[:n]

    def format_context(self, docs: list[RetrievedDoc]) -> str:
        if not docs:
            return ""
        parts = [f"[{i+1}] {d.text}" for i, d in enumerate(docs)]
        return "Relevant context:\n" + "\n---\n".join(parts)

    def store(self, doc_id: str, text: str, metadata: dict | None = None):
        """Convenience wrapper for add_document."""
        self.add_document(doc_id, text, metadata)
