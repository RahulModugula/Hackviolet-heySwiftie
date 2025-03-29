"""Mood and sentiment tracking over time."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum

from app.core.sentiment import analyze_sentiment


class Mood(str, Enum):
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


@dataclass
class MoodEntry:
    timestamp: datetime.datetime
    sentiment_score: float
    mood: Mood
    message_preview: str


class MoodTracker:
    """Track user mood and sentiment patterns over time."""

    def __init__(self, conversation_store):
        self.store = conversation_store

    def analyze_mood(self, session_id: str) -> dict:
        """Analyze mood for a session."""
        history = self.store.get_history(session_id, limit=1000)

        entries = []
        for msg in history:
            if msg["role"] == "user":
                result = analyze_sentiment(msg["content"])
                mood = self._score_to_mood(result.score)
                entries.append(
                    MoodEntry(
                        timestamp=datetime.datetime.utcnow(),
                        sentiment_score=result.score,
                        mood=mood,
                        message_preview=msg["content"][:100],
                    )
                )

        if not entries:
            return {
                "session_id": session_id,
                "average_sentiment": 0.0,
                "overall_mood": "neutral",
                "entries": [],
            }

        avg_sentiment = sum(e.sentiment_score for e in entries) / len(entries)
        overall_mood = self._score_to_mood(avg_sentiment).value

        return {
            "session_id": session_id,
            "average_sentiment": round(avg_sentiment, 2),
            "overall_mood": overall_mood,
            "entry_count": len(entries),
            "mood_distribution": self._get_mood_distribution(entries),
        }

    def get_mood_timeline(self, limit_sessions: int = 10) -> list[dict]:
        """Get mood timeline across recent sessions."""
        sessions = self.store.list_sessions()[:limit_sessions]
        timeline = []

        for session in sessions:
            analysis = self.analyze_mood(session["id"])
            if analysis["entry_count"] > 0:
                timeline.append(
                    {
                        "session_id": session["id"],
                        "mood": analysis["overall_mood"],
                        "sentiment": analysis["average_sentiment"],
                    }
                )

        return timeline

    def _score_to_mood(self, score: float) -> Mood:
        """Convert sentiment score to mood category."""
        if score > 0.5:
            return Mood.VERY_POSITIVE
        elif score > 0.1:
            return Mood.POSITIVE
        elif score > -0.1:
            return Mood.NEUTRAL
        elif score > -0.5:
            return Mood.NEGATIVE
        else:
            return Mood.VERY_NEGATIVE

    def _get_mood_distribution(self, entries: list[MoodEntry]) -> dict:
        """Count moods in entries."""
        dist = {mood.value: 0 for mood in Mood}
        for entry in entries:
            dist[entry.mood.value] += 1
        return dist
