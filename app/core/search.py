"""Full-text conversation search with ranking."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SearchResult:
    session_id: str
    timestamp: datetime
    role: str
    content: str
    relevance_score: float


class ConversationSearcher:
    """Search across conversations with relevance ranking."""

    def __init__(self, conversation_store):
        self.store = conversation_store

    def search(self, query: str, limit: int = 20) -> list[SearchResult]:
        """Full-text search across all conversations."""
        query_terms = self._normalize_query(query)
        if not query_terms:
            return []

        sessions = self.store.list_sessions()
        results = []

        for session in sessions:
            history = self.store.get_history(session["id"], limit=1000)
            for msg in history:
                score = self._score_message(msg["content"], query_terms)
                if score > 0:
                    results.append(
                        SearchResult(
                            session_id=session["id"],
                            timestamp=datetime.utcnow(),
                            role=msg["role"],
                            content=msg["content"],
                            relevance_score=score,
                        )
                    )

        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:limit]

    def _normalize_query(self, query: str) -> list[str]:
        """Extract searchable terms from query."""
        # remove punctuation, split on whitespace
        terms = re.findall(r"\b\w+\b", query.lower())
        # filter out very short terms
        return [t for t in terms if len(t) > 2]

    def _score_message(self, content: str, query_terms: list[str]) -> float:
        """Score a message for relevance to query."""
        content_lower = content.lower()
        score = 0.0

        for term in query_terms:
            # exact term match
            if term in content_lower:
                score += 1.0
                # boost for multiple occurrences
                score += content_lower.count(term) * 0.2

        return min(score, 10.0)  # cap at 10

    def summarize_session(self, session_id: str, max_length: int = 300) -> str:
        """Generate a brief summary of a session."""
        history = self.store.get_history(session_id, limit=1000)
        if not history:
            return ""

        # extract key messages (those with more content or from assistant)
        key_messages = [
            msg["content"]
            for msg in history
            if msg["role"] == "assistant" or len(msg["content"]) > 50
        ][:5]

        summary = " ".join(key_messages)
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return summary
