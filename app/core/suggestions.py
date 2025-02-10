"""Proactive suggestions engine - pattern detection and contextual recommendations."""

from __future__ import annotations

import datetime
import logging
from collections import Counter
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Suggestion:
    text: str
    category: str  # reminder | insight | recommendation | follow_up
    confidence: float
    context: str = ""


class SuggestionEngine:
    """Generates proactive suggestions based on conversation patterns and memory."""

    def __init__(self, memory_manager, task_manager=None):
        self.memory = memory_manager
        self.tasks = task_manager
        self._topic_history: list[tuple[str, datetime.datetime]] = []
        self._interaction_times: list[datetime.datetime] = []

    def record_interaction(self, topics: list[str]):
        now = datetime.datetime.utcnow()
        self._interaction_times.append(now)
        for t in topics:
            self._topic_history.append((t, now))

    def generate(self, current_context: str = "") -> list[Suggestion]:
        suggestions = []

        # check overdue tasks
        if self.tasks:
            overdue = self.tasks.overdue()
            for task in overdue[:3]:
                suggestions.append(
                    Suggestion(
                        text=f"Reminder: '{task.title}' is overdue",
                        category="reminder",
                        confidence=0.9,
                        context=f"Due: {task.due_date}",
                    )
                )

        # recurring topics
        recurring = self._find_recurring_topics()
        for topic, count in recurring[:2]:
            suggestions.append(
                Suggestion(
                    text=f"You've mentioned '{topic}' {count} times recently. Want me to help organize your thoughts on this?",
                    category="insight",
                    confidence=0.6,
                )
            )

        # time-based patterns
        time_suggestion = self._time_based_suggestion()
        if time_suggestion:
            suggestions.append(time_suggestion)

        return suggestions

    def _find_recurring_topics(self, window_days: int = 7) -> list[tuple[str, int]]:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=window_days)
        recent = [t for t, ts in self._topic_history if ts > cutoff]
        counts = Counter(recent)
        return [(t, c) for t, c in counts.most_common(5) if c >= 3]

    def _time_based_suggestion(self) -> Suggestion | None:
        now = datetime.datetime.utcnow()
        hour = now.hour

        if 6 <= hour < 9:
            return Suggestion(
                text="Good morning! Want a summary of what we discussed yesterday?",
                category="follow_up",
                confidence=0.5,
            )
        elif 17 <= hour < 19:
            if self.tasks and self.tasks.list_tasks():
                pending = len(self.tasks.list_tasks())
                return Suggestion(
                    text=f"End of day check: you have {pending} pending tasks.",
                    category="reminder",
                    confidence=0.7,
                )
        return None
