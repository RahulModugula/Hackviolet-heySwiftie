"""Lightweight sentiment analysis and topic extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass

POSITIVE_WORDS = frozenset([
    "good", "great", "awesome", "love", "happy", "excellent", "amazing",
    "wonderful", "fantastic", "nice", "thanks", "thank", "helpful", "perfect",
    "beautiful", "brilliant", "excited", "glad", "enjoy", "appreciated",
])
NEGATIVE_WORDS = frozenset([
    "bad", "terrible", "awful", "hate", "angry", "frustrated", "annoying",
    "horrible", "worst", "sad", "disappointed", "upset", "boring", "ugly",
    "confused", "stuck", "broken", "wrong", "fail", "failed",
])
STOP_WORDS = frozenset([
    "i", "me", "my", "you", "your", "we", "our", "the", "a", "an", "is",
    "are", "was", "were", "be", "been", "have", "has", "had", "do", "does",
    "did", "will", "would", "could", "should", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "it", "its", "this", "that", "not",
    "no", "but", "or", "and", "if", "so", "what", "how", "when", "where",
    "who", "there", "just", "about", "all", "some", "very", "also", "much",
])


@dataclass
class SentimentResult:
    score: float  # -1 to 1
    label: str
    confidence: float


def analyze_sentiment(text: str) -> SentimentResult:
    words = set(re.findall(r"\b\w+\b", text.lower()))
    pos = len(words & POSITIVE_WORDS)
    neg = len(words & NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return SentimentResult(score=0.0, label="neutral", confidence=0.5)
    score = (pos - neg) / total
    label = "positive" if score > 0.1 else "negative" if score < -0.1 else "neutral"
    return SentimentResult(score=score, label=label, confidence=min(total / 5, 1.0))


def extract_topics(text: str, max_topics: int = 5) -> list[str]:
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    candidates = [w for w in words if w not in STOP_WORDS]
    freq: dict[str, int] = {}
    for w in candidates:
        freq[w] = freq.get(w, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)][:max_topics]
