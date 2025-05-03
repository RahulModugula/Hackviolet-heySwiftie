"""Smart context window pruning based on importance."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ContextPruner:
    """Intelligently prune context window to fit token limits."""

    def __init__(self, context_window: int = 20):
        self.context_window = context_window

    def prune_context(self, history: list[dict], max_tokens: int = 4000) -> list[dict]:
        """Prune context to fit token budget."""
        if len(history) <= self.context_window:
            return history

        # keep most recent messages and sample older ones
        kept = history[-self.context_window :]
        return kept

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (4 chars ≈ 1 token)."""
        return len(text) // 4

    def prune_to_token_budget(
        self, history: list[dict], max_tokens: int = 4000
    ) -> list[dict]:
        """Prune context to fit token budget."""
        pruned = []
        token_count = 0

        # add messages in reverse order (most recent first)
        for msg in reversed(history):
            tokens = self.estimate_tokens(msg["content"])
            if token_count + tokens > max_tokens:
                break
            pruned.insert(0, msg)
            token_count += tokens

        return pruned
