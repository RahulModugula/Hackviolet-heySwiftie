"""Tests for new v0.6.0 features."""

import pytest
from datetime import datetime

from app.core.search import ConversationSearcher
from app.core.mood_tracker import MoodTracker
from app.core.habits import HabitTracker
from app.core.export import ExportService
from app.core.summarization import ConversationSummarizer
from app.core.cache import RedisCache, RateLimiter
from app.core.knowledge_graph import KnowledgeGraph
from app.core.context_pruning import ContextPruner


class FakeStore:
    def __init__(self):
        self._messages = []
        self._memories = {}

    def add_message(self, session_id, role, content):
        self._messages.append({"session_id": session_id, "role": role, "content": content})

    def get_history(self, session_id, limit=20):
        msgs = [m for m in self._messages if m["session_id"] == session_id]
        return [{"role": m["role"], "content": m["content"]} for m in msgs[-limit:]]

    def list_sessions(self):
        ids = list({m["session_id"] for m in self._messages})
        return [{"id": i, "title": "", "created_at": str(datetime.utcnow())} for i in ids]

    def get_all_memories(self):
        return list(self._memories.values())


@pytest.fixture
def store():
    return FakeStore()


class TestConversationSearch:
    def test_search_empty(self, store):
        searcher = ConversationSearcher(store)
        results = searcher.search("python")
        assert results == []

    def test_search_finds_message(self, store):
        store.add_message("s1", "user", "I love python programming")
        searcher = ConversationSearcher(store)
        results = searcher.search("python")
        assert len(results) > 0
        assert "python" in results[0].content.lower()


class TestMoodTracker:
    def test_analyze_mood_empty(self, store):
        tracker = MoodTracker(store)
        result = tracker.analyze_mood("s1")
        assert result["overall_mood"] == "neutral"

    def test_analyze_mood_positive(self, store):
        store.add_message("s1", "user", "I love this! It's amazing and wonderful!")
        tracker = MoodTracker(store)
        result = tracker.analyze_mood("s1")
        assert result["average_sentiment"] > 0


class TestConversationSummarizer:
    def test_summarize_empty(self, store):
        summarizer = ConversationSummarizer(store)
        summary = summarizer.summarize("s1")
        assert summary.title == "Empty conversation"

    def test_summarize_with_content(self, store):
        store.add_message("s1", "user", "Tell me about Python")
        store.add_message("s1", "assistant", "Python is a popular programming language used for AI, web development, and data science. It offers simple syntax and powerful libraries.")
        summarizer = ConversationSummarizer(store)
        summary = summarizer.summarize("s1")
        assert len(summary.key_points) > 0


class TestExportService:
    def test_export_session(self, store):
        store.add_message("s1", "user", "hello")
        store.add_message("s1", "assistant", "hi")
        export_svc = ExportService(store, None)
        export = export_svc.export_session("s1")
        assert export["session_id"] == "s1"
        assert len(export["messages"]) == 2


class TestRedisCache:
    def test_cache_set_get(self):
        cache = RedisCache("redis://invalid:0")  # will fall back to memory
        cache.set("key1", {"data": "value"})
        result = cache.get("key1")
        assert result == {"data": "value"}

    def test_cache_delete(self):
        cache = RedisCache("redis://invalid:0")
        cache.set("key1", "value")
        cache.delete("key1")
        assert cache.get("key1") is None


class TestRateLimiter:
    def test_rate_limit_allowed(self):
        cache = RedisCache("redis://invalid:0")
        limiter = RateLimiter(cache, max_requests=3, window_seconds=60)
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is False


class TestContextPruner:
    def test_prune_context(self):
        pruner = ContextPruner(context_window=5)
        history = [{"role": "user", "content": f"msg{i}"} for i in range(10)]
        pruned = pruner.prune_context(history)
        assert len(pruned) <= 5

    def test_token_estimate(self):
        pruner = ContextPruner()
        tokens = pruner.estimate_tokens("hello world")
        assert tokens > 0


class TestKnowledgeGraph:
    def test_add_node(self):
        graph = KnowledgeGraph(None)
        node = graph.add_fact("f1", "Alice likes coffee")
        assert node.id == "f1"
        assert "coffee" in node.content

    def test_relate_facts(self):
        graph = KnowledgeGraph(None)
        graph.add_fact("f1", "Alice likes coffee")
        graph.add_fact("f2", "Coffee is a beverage")
        graph.relate("f1", "f2", "related_to")
        related = graph.get_related_facts("f1")
        assert "f2" in related
