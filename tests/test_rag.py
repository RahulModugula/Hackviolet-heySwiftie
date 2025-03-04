"""Tests for RAG pipeline."""

import pytest
from app.core.rag import RAGPipeline, RetrievedDoc


class FakeVectorStore:
    def __init__(self):
        self._docs: list[tuple[str, str, dict]] = []

    def add(self, doc_id, text, metadata=None):
        self._docs.append((doc_id, text, metadata or {}))

    def query(self, text, n_results=5):
        words = set(text.lower().split())
        scored = []
        for _, doc_text, _ in self._docs:
            doc_words = set(doc_text.lower().split())
            score = len(words & doc_words)
            if score > 0:
                scored.append((score, doc_text))
        scored.sort(reverse=True)
        return [t for _, t in scored[:n_results]]

    def count(self):
        return len(self._docs)


@pytest.fixture
def rag():
    vs = FakeVectorStore()
    pipeline = RAGPipeline(vectorstore=vs, max_docs=3)
    return pipeline


def test_add_and_retrieve(rag):
    rag.add_document("1", "Python is a programming language")
    rag.add_document("2", "Java is another programming language")
    rag.add_document("3", "I love cooking pasta")

    results = rag.retrieve("Python programming")
    assert len(results) > 0
    assert any("Python" in r.text for r in results)


def test_max_docs_respected(rag):
    for i in range(10):
        rag.add_document(str(i), f"document about topic {i} programming")
    results = rag.retrieve("programming topic")
    assert len(results) <= 3


def test_format_context_empty(rag):
    ctx = rag.format_context([])
    assert ctx == ""


def test_format_context_nonempty(rag):
    docs = [RetrievedDoc(text="hello world", score=0.9, source="vector")]
    ctx = rag.format_context(docs)
    assert "hello world" in ctx
    assert "Relevant context" in ctx


def test_hybrid_fusion(rag):
    rag.add_document("a", "machine learning deep neural networks")
    rag.add_document("b", "baking bread yeast flour")
    rag.add_document("c", "machine learning gradient descent optimization")

    results = rag.retrieve("machine learning neural")
    texts = [r.text for r in results]
    # ML docs should rank higher than bread
    assert any("machine learning" in t for t in texts[:2])


def test_bm25_weight_effect():
    vs = FakeVectorStore()
    # high BM25 weight
    rag_bm25 = RAGPipeline(vs, bm25_weight=0.9, vector_weight=0.1, max_docs=5)
    rag_bm25.add_document("1", "exact keyword match test")
    results = rag_bm25.retrieve("exact keyword match")
    assert len(results) > 0


def test_store_convenience(rag):
    rag.store("x", "some text", {"source": "test"})
    results = rag.retrieve("some text")
    assert any("some text" in r.text for r in results)
