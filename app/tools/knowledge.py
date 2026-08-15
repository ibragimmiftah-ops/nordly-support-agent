"""Knowledge base search tool for Nordly documentation.

Provides deterministic text-based search over local Markdown documentation.
No embeddings or network access required.
"""

from dataclasses import dataclass
from pathlib import Path

from app.config import settings


@dataclass
class KnowledgeResult:
    """Single knowledge base search result."""

    document_name: str
    section: str
    snippet: str
    score: float


class KnowledgeBase:
    """In-memory knowledge base loaded from Markdown files."""

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize and load knowledge documents.

        Args:
            base_path: Path to knowledge base directory. Uses settings if None.
        """
        self.base_path = base_path or settings.knowledge_base_dir
        self.documents: dict[str, str] = {}
        self._load_documents()

    def _load_documents(self) -> None:
        """Load all Markdown files from the knowledge base directory."""
        if not self.base_path.exists():
            return

        for md_file in self.base_path.glob("*.md"):
            self.documents[md_file.stem] = md_file.read_text(encoding="utf-8")

    def search(self, query: str, limit: int = 5) -> list[KnowledgeResult]:
        """Search knowledge base for relevant documentation.

        Uses simple keyword matching with section-aware scoring.
        No embeddings or external services required.

        Args:
            query: Search query string.
            limit: Maximum number of results to return.

        Returns:
            List of KnowledgeResult objects ordered by relevance.
        """
        query_terms = [t.lower() for t in query.split() if len(t) > 2]
        if not query_terms:
            return []

        results: list[KnowledgeResult] = []

        for doc_name, content in self.documents.items():
            sections = self._split_into_sections(content)
            for section_title, section_text in sections:
                score = self._calculate_score(query_terms, section_title, section_text)
                if score > 0:
                    snippet = self._extract_snippet(section_text, query_terms)
                    results.append(
                        KnowledgeResult(
                            document_name=doc_name,
                            section=section_title,
                            snippet=snippet,
                            score=score,
                        )
                    )

        # Sort by score descending and limit
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def _split_into_sections(self, content: str) -> list[tuple[str, str]]:
        """Split Markdown content into sections by headers.

        Returns:
            List of (section_title, section_text) tuples.
        """
        lines = content.split("\n")
        sections: list[tuple[str, str]] = []
        current_title = "Introduction"
        current_lines: list[str] = []

        for line in lines:
            if line.startswith("#"):
                if current_lines:
                    sections.append((current_title, "\n".join(current_lines).strip()))
                current_title = line.lstrip("#").strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections.append((current_title, "\n".join(current_lines).strip()))

        return sections

    def _calculate_score(
        self, query_terms: list[str], section_title: str, section_text: str
    ) -> float:
        """Calculate relevance score for a section.

        Args:
            query_terms: Lowercase query terms.
            section_title: Section title.
            section_text: Section body text.

        Returns:
            Relevance score (higher = more relevant).
        """
        title_lower = section_title.lower()
        text_lower = section_text.lower()

        score = 0.0
        for term in query_terms:
            # Title matches weighted heavily
            if term in title_lower:
                score += 3.0
            # Exact word matches in text
            if term in text_lower:
                score += 1.0
            # Count occurrences
            score += text_lower.count(term) * 0.1

        return score

    def _extract_snippet(self, section_text: str, query_terms: list[str]) -> str:
        """Extract a relevant snippet from section text.

        Args:
            section_text: Full section text.
            query_terms: Query terms to find.

        Returns:
            Truncated snippet around first query match.
        """
        text_lower = section_text.lower()
        best_pos = -1

        for term in query_terms:
            pos = text_lower.find(term)
            if pos != -1 and (best_pos == -1 or pos < best_pos):
                best_pos = pos

        if best_pos == -1:
            return section_text[:300] + "..." if len(section_text) > 300 else section_text

        start = max(0, best_pos - 100)
        end = min(len(section_text), best_pos + 200)
        snippet = section_text[start:end]

        if start > 0:
            snippet = "..." + snippet
        if end < len(section_text):
            snippet = snippet + "..."

        return snippet


# Global knowledge base instance
_knowledge_base: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    """Get or create the global knowledge base instance."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base


def search_knowledge_base(query: str, limit: int = 5) -> list[KnowledgeResult]:
    """Search the knowledge base.

    Args:
        query: Search query.
        limit: Maximum results.

    Returns:
        List of knowledge results.
    """
    kb = get_knowledge_base()
    return kb.search(query, limit=limit)
