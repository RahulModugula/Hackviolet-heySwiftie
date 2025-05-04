"""Dependency injection - singleton wiring."""

from __future__ import annotations

import logging
import os

from app.config import settings
from app.core.llm import get_provider
from app.core.memory import MemoryManager
from app.core.rag import RAGPipeline
from app.core.tasks import TaskManager
from app.core.tools import ToolRegistry
from app.core.suggestions import SuggestionEngine
from app.core.voice import SpeechToText, TextToSpeech
from app.db.sqlite import ConversationStore
from app.db.vector import VectorStore
from app.services.chat import ChatService
from app.services.voice import VoiceService
from app.services.knowledge import create_knowledge_base

logger = logging.getLogger(__name__)

os.makedirs("data", exist_ok=True)

# --- storage ---
conversation_store = ConversationStore(settings.db_url)
vector_store = VectorStore(settings.chroma_persist_dir)

# --- LLM provider ---
if settings.privacy_mode:
    # force local inference in privacy mode
    _provider = settings.llm_provider if settings.llm_provider in ("ollama", "mlx") else "ollama"
else:
    _provider = settings.llm_provider

llm_provider = get_provider(
    provider=_provider,
    api_key=settings.openai_api_key,
    model=settings.openai_model if _provider == "openai" else settings.ollama_model,
    base_url=settings.ollama_base_url,
)

# --- core ---
memory_manager = MemoryManager(
    conversation_store,
    context_window=settings.context_window,
    decay_hours=settings.memory_decay_hours,
)

# reranker (optional, graceful degradation)
_reranker = None
try:
    from sentence_transformers import CrossEncoder
    _reranker = CrossEncoder(settings.reranker_model)
    logger.info("Cross-encoder reranker loaded")
except Exception:
    logger.info("Reranker not available, skipping")

rag_pipeline = RAGPipeline(
    vectorstore=vector_store,
    bm25_weight=settings.bm25_weight,
    vector_weight=settings.vector_weight,
    max_docs=settings.max_retrieval_docs,
    reranker=_reranker,
)

task_manager = TaskManager()
tool_registry = ToolRegistry()
suggestion_engine = SuggestionEngine(memory_manager, task_manager)

# --- services ---
chat_service = ChatService(
    llm=llm_provider,
    memory=memory_manager,
    rag=rag_pipeline,
    tools=tool_registry,
    suggestions=suggestion_engine,
)

# --- voice (lazy load) ---
_stt: SpeechToText | None = None
_tts: TextToSpeech | None = None
_voice_service: VoiceService | None = None


def get_voice_service() -> VoiceService:
    global _stt, _tts, _voice_service
    if _voice_service is None:
        _stt = SpeechToText(model_size=settings.whisper_model)
        _tts = TextToSpeech(model=settings.tts_model, speaker=settings.tts_speaker)
        _voice_service = VoiceService(_stt, _tts)
    return _voice_service


knowledge_base = create_knowledge_base(
    rag_pipeline,
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap,
)

# --- NEW FEATURES (0.6.0) ---
# Redis cache
from app.core.cache import RedisCache, RateLimiter

redis_cache = RedisCache(settings.redis_url)
rate_limiter = RateLimiter(redis_cache, max_requests=100, window_seconds=60)

# Conversation search
from app.core.search import ConversationSearcher

conversation_searcher = ConversationSearcher(conversation_store)

# Export service
from app.core.export import ExportService

export_service = ExportService(conversation_store, memory_manager)

# Summarization
from app.core.summarization import ConversationSummarizer

summarizer = ConversationSummarizer(conversation_store)

# Mood tracking
from app.core.mood_tracker import MoodTracker

mood_tracker = MoodTracker(conversation_store)

# Habit tracking
from app.core.habits import HabitTracker

habit_tracker = HabitTracker(suggestion_engine)

# Plugin system
from app.core.plugins import PluginManager

plugin_manager = PluginManager(plugins_dir="./plugins")
plugin_manager.load_plugins(tool_registry)

# Reminders
from app.core.reminders import ReminderEngine

reminder_engine = ReminderEngine(task_manager, suggestion_engine)

# Knowledge graph
from app.core.knowledge_graph import KnowledgeGraph

knowledge_graph = KnowledgeGraph(memory_manager)

# Context pruning
from app.core.context_pruning import ContextPruner

context_pruner = ContextPruner(context_window=settings.context_window)
