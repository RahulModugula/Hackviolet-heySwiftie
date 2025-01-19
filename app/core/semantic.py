"""Semantic memory - extract facts and preferences from conversations."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.core.memory import SemanticFact

logger = logging.getLogger(__name__)

# patterns for extracting user facts
FACT_PATTERNS = [
    # "I am/I'm X"
    (r"(?:i am|i'm)\s+(?:a\s+)?(.+?)(?:\.|,|!|\?|$)", "user", "is"),
    # "my name is X"
    (r"my name is\s+(\w+)", "user", "name_is"),
    # "I live in X"
    (r"i live in\s+(.+?)(?:\.|,|!|\?|$)", "user", "lives_in"),
    # "I work at/for X"
    (r"i work (?:at|for)\s+(.+?)(?:\.|,|!|\?|$)", "user", "works_at"),
    # "I like/love X"
    (r"i (?:like|love|enjoy)\s+(.+?)(?:\.|,|!|\?|$)", "user", "likes"),
    # "I don't like / I hate X"
    (r"i (?:don't like|hate|dislike)\s+(.+?)(?:\.|,|!|\?|$)", "user", "dislikes"),
    # "my favorite X is Y"
    (r"my (?:favorite|favourite)\s+(\w+)\s+is\s+(.+?)(?:\.|,|!|\?|$)", "user", "favorite_{0}"),
    # "I'm from X"
    (r"i'm from\s+(.+?)(?:\.|,|!|\?|$)", "user", "from"),
    # "I have X"
    (r"i have (?:a\s+)?(.+?)(?:\.|,|!|\?|$)", "user", "has"),
    # "I study/studied X"
    (r"i (?:study|studied|am studying)\s+(.+?)(?:\.|,|!|\?|$)", "user", "studies"),
    # preferences: "I prefer X"
    (r"i prefer\s+(.+?)(?:\.|,|!|\?|$)", "user", "prefers"),
]


def extract_facts(text: str) -> list[SemanticFact]:
    """Extract semantic facts from user text using pattern matching."""
    facts = []
    text_lower = text.lower().strip()

    for pattern, subject, predicate in FACT_PATTERNS:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            groups = match.groups()
            if len(groups) == 1:
                value = groups[0].strip()
                pred = predicate
            elif len(groups) == 2:
                # for patterns like "favorite X is Y"
                pred = predicate.format(groups[0].strip())
                value = groups[1].strip()
            else:
                continue

            if len(value) > 2 and len(value) < 100:
                facts.append(
                    SemanticFact(
                        subject=subject, predicate=pred, value=value, confidence=0.8
                    )
                )

    return facts


# topic / sentiment keywords for importance scoring
IMPORTANT_TOPICS = frozenset([
    "name", "birthday", "family", "work", "job", "school", "health",
    "home", "address", "phone", "email", "schedule", "meeting",
    "deadline", "project", "goal", "plan", "preference", "allergy",
])


def estimate_importance(text: str) -> float:
    """Estimate how important a message is for long-term memory."""
    words = set(text.lower().split())
    topic_hits = len(words & IMPORTANT_TOPICS)

    # personal info is more important
    has_personal = bool(re.search(r'\b(my|i am|i\'m|i have|i live|i work)\b', text.lower()))
    has_question = "?" in text
    has_instruction = bool(re.search(r'\b(remember|don\'t forget|always|never)\b', text.lower()))

    score = 0.3  # baseline
    score += min(topic_hits * 0.1, 0.3)
    if has_personal:
        score += 0.15
    if has_instruction:
        score += 0.2
    if has_question:
        score -= 0.1  # questions are less memorable than statements

    return min(max(score, 0.1), 1.0)
