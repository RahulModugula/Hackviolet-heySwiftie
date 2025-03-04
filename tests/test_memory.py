"""Tests for memory system."""

import datetime
import math
import pytest

from app.core.memory import Memory, MemoryManager, MemoryType, SemanticFact
from app.core.semantic import extract_facts, estimate_importance


class FakeStore:
    """In-memory store for testing."""
    def __init__(self):
        self._messages: list[dict] = []
        self._memories: dict[str, Memory] = {}

    def add_message(self, session_id, role, content):
        self._messages.append({"session_id": session_id, "role": role, "content": content})

    def get_history(self, session_id, limit=20):
        msgs = [m for m in self._messages if m["session_id"] == session_id]
        return [{"role": m["role"], "content": m["content"]} for m in msgs[-limit:]]

    def list_sessions(self):
        ids = list({m["session_id"] for m in self._messages})
        return [{"id": i, "title": "", "created_at": str(datetime.datetime.utcnow())} for i in ids]

    def add_memory(self, memory):
        self._memories[memory.id] = memory

    def search_memories(self, query, memory_type=None, limit=20):
        results = list(self._memories.values())
        if memory_type:
            results = [m for m in results if m.type == memory_type]
        words = query.lower().split()
        results = [m for m in results if any(w in m.content.lower() for w in words)]
        return results[:limit]

    def get_all_memories(self):
        return list(self._memories.values())

    def delete_memory(self, memory_id):
        self._memories.pop(memory_id, None)


@pytest.fixture
def store():
    return FakeStore()


@pytest.fixture
def manager(store):
    return MemoryManager(store, context_window=5, decay_hours=168.0)


def test_save_and_retrieve_history(manager):
    manager.save("s1", "user", "hello")
    manager.save("s1", "assistant", "hi there")
    history = manager.get_context("s1")
    assert len(history) == 2
    assert history[0]["role"] == "user"


def test_context_window_limit(manager):
    for i in range(10):
        manager.save("s2", "user", f"message {i}")
    history = manager.get_context("s2")
    assert len(history) <= 5


def test_episodic_memory_created(manager):
    mem = manager.create_episodic("user mentioned they love coffee", importance=0.7)
    assert mem.type == MemoryType.EPISODIC
    assert mem.importance == 0.7


def test_semantic_memory_created(manager):
    fact = SemanticFact(subject="user", predicate="likes", value="coffee")
    mem = manager.create_semantic(fact)
    assert mem.type == MemoryType.SEMANTIC
    assert "coffee" in mem.content


def test_semantic_fact_deduplication(manager):
    fact1 = SemanticFact(subject="user", predicate="name_is", value="Alice")
    fact2 = SemanticFact(subject="user", predicate="name_is", value="Bob")
    manager.create_semantic(fact1)
    manager.create_semantic(fact2)
    facts = manager.get_user_facts()
    name_facts = [f for f in facts if f.predicate == "name_is"]
    assert len(name_facts) == 1
    assert name_facts[0].value == "Bob"


def test_memory_decay():
    mem = Memory(
        id="test",
        type=MemoryType.EPISODIC,
        content="old memory",
        importance=0.5,
        created_at=datetime.datetime.utcnow() - datetime.timedelta(days=30),
    )
    score = mem.relevance_score(decay_hours=168.0)
    # 30 days is much longer than 7-day half-life, score should be low
    assert score < 0.3


def test_memory_age_hours():
    mem = Memory(
        id="test",
        type=MemoryType.EPISODIC,
        content="recent",
        importance=0.5,
        created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=2),
    )
    assert abs(mem.age_hours - 2.0) < 0.1


def test_recall_relevance_order(manager):
    manager.create_episodic("user loves hiking in mountains", importance=0.8)
    manager.create_episodic("user works as software engineer", importance=0.6)
    results = manager.recall("hiking mountains")
    assert len(results) > 0
    assert "hiking" in results[0].content.lower()


def test_consolidate_removes_old(store, manager):
    old = Memory(
        id="old_mem",
        type=MemoryType.EPISODIC,
        content="old unimportant memory",
        importance=0.1,
        created_at=datetime.datetime.utcnow() - datetime.timedelta(days=60),
    )
    store.add_memory(old)
    manager.consolidate()
    remaining = store.get_all_memories()
    assert not any(m.id == "old_mem" for m in remaining)


class TestSemanticExtraction:
    def test_extract_name(self):
        facts = extract_facts("My name is Alice")
        assert any(f.predicate == "name_is" and f.value == "alice" for f in facts)

    def test_extract_location(self):
        facts = extract_facts("I live in San Francisco")
        assert any("san francisco" in f.value for f in facts)

    def test_extract_preference(self):
        facts = extract_facts("I love hiking and coffee")
        assert any("hiking" in f.value or "coffee" in f.value for f in facts)

    def test_extract_work(self):
        facts = extract_facts("I work at Google")
        assert any("google" in f.value for f in facts)

    def test_importance_high_for_personal(self):
        score = estimate_importance("Remember that I have a meeting with my boss tomorrow")
        assert score > 0.5

    def test_importance_low_for_question(self):
        score = estimate_importance("what time is it?")
        assert score < 0.5
