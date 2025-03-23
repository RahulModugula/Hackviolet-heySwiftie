"""Conversation summarization using extractive methods."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Summary:
    session_id: str
    title: str
    key_points: list[str]
    duration_minutes: float


class ConversationSummarizer:
    """Summarize conversations using extractive methods."""

    def __init__(self, conversation_store):
        self.store = conversation_store

    def summarize(self, session_id: str, max_points: int = 5) -> Summary:
        """Create extractive summary of conversation."""
        history = self.store.get_history(session_id, limit=1000)

        if not history:
            return Summary(
                session_id=session_id,
                title="Empty conversation",
                key_points=[],
                duration_minutes=0.0,
            )

        # extract assistant messages (more likely to be summaries)
        assistant_msgs = [m["content"] for m in history if m["role"] == "assistant"]

        # simple extractive: take longest/most substantive responses
        scored = [
            (msg, len(msg.split()), self._substance_score(msg))
            for msg in assistant_msgs
        ]
        scored.sort(key=lambda x: (x[2], x[1]), reverse=True)

        key_points = [msg for msg, _, _ in scored[:max_points]]

        # estimate title from first user message
        user_msgs = [m["content"] for m in history if m["role"] == "user"]
        title = (
            user_msgs[0][:50] + "..."
            if user_msgs and len(user_msgs[0]) > 50
            else user_msgs[0] if user_msgs else "Conversation"
        )

        return Summary(
            session_id=session_id, title=title, key_points=key_points, duration_minutes=0.0
        )

    def _substance_score(self, text: str) -> float:
        """Score text for substantiveness."""
        if not text:
            return 0.0
        word_count = len(text.split())
        # longer, more detailed responses score higher
        return min(word_count / 50, 1.0)
