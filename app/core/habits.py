"""Habit and pattern detection from conversation topics."""

from __future__ import annotations

import datetime
import logging
from collections import Counter
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Habit:
    topic: str
    frequency: int
    first_mentioned: datetime.datetime
    last_mentioned: datetime.datetime
    confidence: float


class HabitTracker:
    """Detect recurring patterns and habits from conversations."""

    def __init__(self, suggestion_engine):
        self.suggestions = suggestion_engine

    def detect_habits(self, min_occurrences: int = 3) -> list[Habit]:
        """Detect recurring topics/habits."""
        if not self.suggestions._topic_history:
            return []

        # count topic occurrences
        topic_counts = Counter([t for t, _ in self.suggestions._topic_history])

        habits = []
        for topic, count in topic_counts.most_common():
            if count >= min_occurrences:
                # find timestamps
                timestamps = [ts for t, ts in self.suggestions._topic_history if t == topic]
                if timestamps:
                    confidence = min(count / 10, 1.0)  # normalize to 0-1
                    habits.append(
                        Habit(
                            topic=topic,
                            frequency=count,
                            first_mentioned=min(timestamps),
                            last_mentioned=max(timestamps),
                            confidence=confidence,
                        )
                    )

        return sorted(habits, key=lambda h: h.confidence, reverse=True)

    def get_habit_insights(self) -> dict:
        """Generate insights about detected habits."""
        habits = self.detect_habits()

        if not habits:
            return {
                "total_habits": 0,
                "habits": [],
                "insights": ["Keep chatting to build habit patterns!"],
            }

        insights = []

        # most frequent habit
        if habits:
            top_habit = habits[0]
            insights.append(
                f"Your most frequent topic is '{top_habit.topic}' "
                f"(mentioned {top_habit.frequency} times)"
            )

        # recent habits
        recent = [h for h in habits if self._is_recent(h.last_mentioned)]
        if recent:
            topics = ", ".join([h.topic for h in recent[:3]])
            insights.append(f"Recently interested in: {topics}")

        return {
            "total_habits": len(habits),
            "habits": [
                {
                    "topic": h.topic,
                    "frequency": h.frequency,
                    "confidence": round(h.confidence, 2),
                }
                for h in habits[:10]
            ],
            "insights": insights,
        }

    def _is_recent(self, timestamp: datetime.datetime, days: int = 7) -> bool:
        """Check if timestamp is within recent window."""
        return (datetime.datetime.utcnow() - timestamp).days <= days
