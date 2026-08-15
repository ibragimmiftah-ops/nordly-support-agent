"""Deterministic offline retrieval with versioned chunks and citations."""

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass

_TOKEN = re.compile(r"[a-zA-Z0-9_]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.casefold())


def deterministic_embedding(text: str, dimensions: int = 256) -> tuple[float, ...]:
    """Create a stable signed hashing vector suitable for offline tests."""
    vector = [0.0] * dimensions
    for token, count in Counter(_tokens(text)).items():
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[index] += sign * (1.0 + math.log(count))
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return tuple(vector)


@dataclass(frozen=True)
class KnowledgeDocument:
    """Versioned source document."""

    document_id: str
    title: str
    content: str
    version: str
    source: str


@dataclass(frozen=True)
class KnowledgeChunk:
    """Addressable document fragment with deterministic vector."""

    chunk_id: str
    document_id: str
    text: str
    version: str
    source: str
    embedding: tuple[float, ...]


@dataclass(frozen=True)
class RetrievalResult:
    """Relevant chunk and citation metadata."""

    chunk: KnowledgeChunk
    score: float

    @property
    def citation(self) -> str:
        """Return a stable citation carrying source version and chunk."""
        return f"[{self.chunk.source}@{self.chunk.version}#{self.chunk.chunk_id}]"


def chunk_document(
    document: KnowledgeDocument, chunk_size: int = 120, overlap: int = 20
) -> list[KnowledgeChunk]:
    """Split a document by words with deterministic overlap and IDs."""
    if chunk_size < 1 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Require chunk_size > overlap >= 0")
    words = document.content.split()
    chunks: list[KnowledgeChunk] = []
    step = chunk_size - overlap
    for index, start in enumerate(range(0, len(words), step)):
        text = " ".join(words[start : start + chunk_size])
        if not text:
            continue
        chunk_id = f"{document.document_id}-{index}"
        chunks.append(
            KnowledgeChunk(
                chunk_id=chunk_id,
                document_id=document.document_id,
                text=text,
                version=document.version,
                source=document.source,
                embedding=deterministic_embedding(text),
            )
        )
    return chunks


class OfflineVectorIndex:
    """In-memory cosine retrieval without an embedding API."""

    def __init__(self, chunks: list[KnowledgeChunk]) -> None:
        """Initialize an immutable in-memory chunk index."""
        self._chunks = tuple(chunks)

    @classmethod
    def from_documents(
        cls, documents: list[KnowledgeDocument], chunk_size: int = 120, overlap: int = 20
    ) -> "OfflineVectorIndex":
        """Build an index from versioned source documents."""
        return cls(
            [
                chunk
                for document in documents
                for chunk in chunk_document(document, chunk_size, overlap)
            ]
        )

    def search(self, query: str, limit: int = 5, min_score: float = 0.05) -> list[RetrievalResult]:
        """Return relevant chunks in deterministic score/ID order."""
        if not query.strip() or limit < 1:
            return []
        query_vector = deterministic_embedding(query)
        results = [
            RetrievalResult(
                chunk,
                sum(a * b for a, b in zip(query_vector, chunk.embedding, strict=True)),
            )
            for chunk in self._chunks
        ]
        relevant = [result for result in results if result.score >= min_score]
        return sorted(relevant, key=lambda result: (-result.score, result.chunk.chunk_id))[:limit]
