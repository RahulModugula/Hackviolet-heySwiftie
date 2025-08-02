# Architecture Deep Dive

## System Overview

```
┌──────────────────────────────────────────────────┐
│              iOS Client (SwiftUI)                │
│  - Chat with streaming                           │
│  - Voice recording/playback                      │
│  - Task & memory browsing                        │
│  - Settings management                           │
└──────────────┬───────────────────────────────────┘
               │ HTTP/WebSocket
┌──────────────▼───────────────────────────────────┐
│            FastAPI Server (0.6.0)                │
│  ┌─────────────────────────────────────────────┐ │
│  │  API Layer                                  │ │
│  │  - /api/chat, /api/voice, /api/memory      │ │
│  │  - /api/search, /api/features               │ │
│  │  - /ws/chat (WebSocket)                     │ │
│  └─────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │  Service Layer                              │ │
│  │  - ChatService (orchestration)              │ │
│  │  - VoiceService (STT/TTS)                   │ │
│  │  - ExportService                            │ │
│  │  - PluginManager                            │ │
│  └─────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │  Core Features (v0.6.0)                    │ │
│  │  - MemoryManager (episodic/semantic)        │ │
│  │  - RAGPipeline (hybrid search+rerank)       │ │
│  │  - MoodTracker, HabitTracker                │ │
│  │  - KnowledgeGraph, ContextPruner            │ │
│  │  - ConversationSearcher                     │ │
│  │  - ReminderEngine, ToolRegistry             │ │
│  └─────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │  LLM Abstraction                            │ │
│  │  - OpenAI (cloud)                           │ │
│  │  - Ollama (local)                           │ │
│  │  - MLX (Apple Silicon)                      │ │
│  └─────────────────────────────────────────────┘ │
└──────────────┬────────┬──────────┬───────────────┘
               │        │          │
        ┌──────▼──┐ ┌───▼────┐ ┌──▼─────────┐
        │ SQLite  │ │ ChromaDB│ │Redis Cache │
        │ Store   │ │ Vector  │ │ & Rate Lim │
        └─────────┘ └────────┘ └────────────┘
```

## Data Flow: Chat with Memory

```
1. User Message
   ↓
2. Memory Recall (semantic search)
   ↓
3. RAG Retrieval (BM25 + vector + rerank)
   ↓
4. Context Building
   - Recent conversation history
   - Retrieved documents
   - Long-term memories
   - User facts
   ↓
5. LLM Generation
   - OpenAI / Ollama / MLX
   ↓
6. Response Persistence
   - Save to SQLite
   - Store in RAG corpus
   - Extract & save facts
   ↓
7. Pattern Recording
   - Track topics for habits
   - Record sentiment for mood
   ↓
8. Stream to Client
```

## Memory System (Three-Tier)

**Episodic**: Conversation events with importance scoring and exponential decay
- Example: "User mentioned vacation plans"
- Decay: 7-day half-life (configurable)

**Semantic**: Extracted facts and preferences
- Example: `user.job = "engineer"`, `user.likes = "hiking"`
- Deduplication by subject+predicate

**Procedural**: Learned patterns (framework exists, extensible)
- Currently auto-generated from topic frequency

## RAG Pipeline (Hybrid & Reranked)

1. **BM25 Search**: Keyword-based retrieval (40% weight default)
2. **Vector Search**: Semantic similarity via embeddings (60% weight)
3. **Reciprocal Rank Fusion**: Combine both rankings
4. **Cross-Encoder Reranking**: ms-marco-MiniLM re-scores top-k
5. **Context Formatting**: Numbered list for system prompt injection

## Plugin Architecture

Plugins are Python modules in `./plugins/`:

```python
# Each plugin must define PLUGIN object
PLUGIN = {
    'name': 'my_plugin',
    'version': '0.1.0',
    'register_tools': async_register_func
}
```

At startup, PluginManager:
1. Scans `./plugins/` directory
2. Dynamically imports modules
3. Calls `register_tools()` for each plugin
4. Tool registry includes plugins + built-ins

## v0.6.0 New Components

**ConversationSearcher**: Full-text search with TF-IDF-like scoring
**MoodTracker**: Sentiment analysis + historical timeline
**HabitTracker**: Topic frequency detection + confidence
**KnowledgeGraph**: Fact nodes + relationships + multi-hop traversal
**ContextPruner**: Token-aware window management
**ExportService**: JSON serialization of all data
**ReminderEngine**: Pattern + time-based triggers
**RedisCache**: Session caching + rate limiting

All components are wired through dependency injection in `dependencies.py`.
