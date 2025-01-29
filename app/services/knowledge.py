"""Knowledge base service."""

from __future__ import annotations

from app.core.knowledge import KnowledgeBase, SemanticChunker
from app.core.rag import RAGPipeline


def create_knowledge_base(rag: RAGPipeline, chunk_size: int = 512, chunk_overlap: int = 64) -> KnowledgeBase:
    chunker = SemanticChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return KnowledgeBase(rag, chunker)
