"""Memory system - episodic, semantic, and procedural memory with decay."""

from __future__ import annotations

import datetime
import hashlib
import logging
import math
import uuid
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    EPISODIC = "episodic"  # conversation events, interactions
    SEMANTIC = "semantic"  # facts, preferences, knowledge about user
    PROCEDURAL = "procedural"  # learned patterns, how to do things


@dataclass
class Memory:
    id: str
    type: MemoryType
    content: str
    importance: float  # 0-1, how important this memory is
    created_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    last_accessed: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    access_count: int = 0
    metadata: dict = field(default_factory=dict)
    embedding: list[float] | None = None

    @property
    def age_hours(self) -> float:
        delta = datetime.datetime.utcnow() - self.created_at
        return delta.total_seconds() / 3600

    def relevance_score(self, decay_hours: float = 168.0) -> float:
        """Compute relevance combining importance, recency, and access frequency."""
        recency = math.exp(-0.693 * self.age_hours / decay_hours)  # half-life decay
        frequency_boost = min(self.access_count / 10, 1.0) * 0.2
        return self.importance * 0.5 + recency * 0.3 + frequency_boost


@dataclass
class SemanticFact:
    """Extracted fact about the user or world."""
    subject: str
    predicate: str
    value: str
    confidence: float = 1.0
    source_memory_id: str = ""

    @property
    def key(self) -> str:
        return hashlib.md5(f"{self.subject}:{self.predicate}".encode()).hexdigest()

    def __str__(self):
        return f"{self.subject} {self.predicate} {self.value}"


class MemoryManager:
    """Manages episodic, semantic, and procedural memories."""

    def __init__(self, store, context_window: int = 20, decay_hours: float = 168.0):
        self.store = store
        self.context_window = context_window
        self.decay_hours = decay_hours
        self._semantic_facts: dict[str, SemanticFact] = {}

    def get_context(self, session_id: str) -> list[dict]:
        return self.store.get_history(session_id, limit=self.context_window)

    def save(self, session_id: str, role: str, content: str):
        self.store.add_message(session_id, role, content)

    def get_sessions(self):
        return self.store.list_sessions()

    def add_memory(self, memory: Memory):
        """Store a memory for later retrieval."""
        self.store.add_memory(memory)
        logger.debug("Stored %s memory: %s", memory.type, memory.id)

    def create_episodic(self, content: str, importance: float = 0.5, **meta) -> Memory:
        mem = Memory(
            id=str(uuid.uuid4()),
            type=MemoryType.EPISODIC,
            content=content,
            importance=importance,
            metadata=meta,
        )
        self.add_memory(mem)
        return mem

    def create_semantic(self, fact: SemanticFact, importance: float = 0.7) -> Memory:
        """Store a semantic fact. Overwrites if same subject+predicate exists."""
        self._semantic_facts[fact.key] = fact
        mem = Memory(
            id=fact.key,
            type=MemoryType.SEMANTIC,
            content=str(fact),
            importance=importance,
            metadata={"subject": fact.subject, "predicate": fact.predicate, "value": fact.value},
        )
        self.add_memory(mem)
        return mem

    def recall(
        self,
        query: str,
        memory_type: MemoryType | None = None,
        limit: int = 10,
    ) -> list[Memory]:
        """Recall relevant memories, ranked by relevance."""
        memories = self.store.search_memories(query, memory_type=memory_type, limit=limit * 2)
        # re-rank by relevance score
        for m in memories:
            m._score = m.relevance_score(self.decay_hours)
        memories.sort(key=lambda m: m._score, reverse=True)
        return memories[:limit]

    def get_user_facts(self) -> list[SemanticFact]:
        return list(self._semantic_facts.values())

    def consolidate(self):
        """Consolidate memories - merge similar episodic memories, prune low-relevance ones."""
        memories = self.store.get_all_memories()
        pruned = 0
        for mem in memories:
            score = mem.relevance_score(self.decay_hours)
            if score < 0.05 and mem.type == MemoryType.EPISODIC:
                self.store.delete_memory(mem.id)
                pruned += 1
        if pruned:
            logger.info("Consolidated memories: pruned %d low-relevance entries", pruned)
