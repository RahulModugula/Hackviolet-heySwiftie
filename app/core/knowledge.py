"""Knowledge base ingestion - PDFs, URLs, markdown, plain text."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Document:
    content: str
    source: str
    doc_type: str  # pdf | url | markdown | text
    metadata: dict | None = None


@dataclass
class Chunk:
    text: str
    doc_id: str
    chunk_index: int
    source: str
    metadata: dict | None = None


class SemanticChunker:
    """Split documents into semantically meaningful chunks."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, document: Document) -> list[Chunk]:
        text = document.content
        doc_id = hashlib.md5(text[:200].encode()).hexdigest()

        # try paragraph-based splitting first
        paragraphs = self._split_paragraphs(text)
        chunks = []
        current = ""
        chunk_idx = 0

        for para in paragraphs:
            if len(current) + len(para) > self.chunk_size and current:
                chunks.append(
                    Chunk(
                        text=current.strip(),
                        doc_id=doc_id,
                        chunk_index=chunk_idx,
                        source=document.source,
                        metadata=document.metadata,
                    )
                )
                # overlap: keep tail of current chunk
                overlap_text = current[-self.chunk_overlap :] if self.chunk_overlap else ""
                current = overlap_text + para + "\n"
                chunk_idx += 1
            else:
                current += para + "\n"

        if current.strip():
            chunks.append(
                Chunk(
                    text=current.strip(),
                    doc_id=doc_id,
                    chunk_index=chunk_idx,
                    source=document.source,
                    metadata=document.metadata,
                )
            )

        return chunks

    def _split_paragraphs(self, text: str) -> list[str]:
        """Split on double newlines, headers, or long single paragraphs."""
        # split on double newlines or markdown headers
        parts = re.split(r"\n\n+|(?=^#{1,3}\s)", text, flags=re.MULTILINE)
        result = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if len(part) > self.chunk_size * 2:
                # sentence-level splitting for very long paragraphs
                sentences = re.split(r"(?<=[.!?])\s+", part)
                result.extend(sentences)
            else:
                result.append(part)
        return result


class DocumentLoader:
    """Load documents from various sources."""

    @staticmethod
    async def load_pdf(path: str | Path) -> Document:
        """Extract text from PDF."""
        import asyncio

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        def _extract():
            try:
                import fitz  # pymupdf

                doc = fitz.open(str(path))
                text = "\n\n".join(page.get_text() for page in doc)
                doc.close()
                return text
            except ImportError:
                # fallback to pdfplumber
                import pdfplumber

                with pdfplumber.open(str(path)) as pdf:
                    return "\n\n".join(
                        page.extract_text() or "" for page in pdf.pages
                    )

        text = await asyncio.to_thread(_extract)
        return Document(content=text, source=str(path), doc_type="pdf")

    @staticmethod
    async def load_url(url: str) -> Document:
        """Fetch and extract text from URL."""
        import httpx

        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url, timeout=30.0)
            resp.raise_for_status()

        html = resp.text
        # simple html to text (strip tags)
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        return Document(content=text, source=url, doc_type="url")

    @staticmethod
    async def load_text(path: str | Path) -> Document:
        """Load plain text or markdown file."""
        import asyncio

        path = Path(path)
        text = await asyncio.to_thread(path.read_text, "utf-8")
        doc_type = "markdown" if path.suffix in (".md", ".mdx") else "text"
        return Document(content=text, source=str(path), doc_type=doc_type)


class KnowledgeBase:
    """Manages document ingestion into the RAG pipeline."""

    def __init__(self, rag_pipeline, chunker: SemanticChunker | None = None):
        self.rag = rag_pipeline
        self.chunker = chunker or SemanticChunker()
        self.loader = DocumentLoader()
        self._ingested: dict[str, int] = {}  # source -> chunk count

    async def ingest(self, source: str) -> int:
        """Ingest a document from path or URL."""
        if source.startswith(("http://", "https://")):
            doc = await self.loader.load_url(source)
        elif source.endswith(".pdf"):
            doc = await self.loader.load_pdf(source)
        else:
            doc = await self.loader.load_text(source)

        chunks = self.chunker.chunk(doc)
        for chunk in chunks:
            chunk_id = f"{chunk.doc_id}_{chunk.chunk_index}"
            self.rag.store(
                doc_id=chunk_id,
                text=chunk.text,
                metadata={"source": chunk.source, "chunk_index": chunk.chunk_index},
            )

        self._ingested[source] = len(chunks)
        logger.info("Ingested %s: %d chunks", source, len(chunks))
        return len(chunks)

    @property
    def stats(self) -> dict:
        return {
            "documents": len(self._ingested),
            "total_chunks": sum(self._ingested.values()),
            "sources": list(self._ingested.keys()),
        }
