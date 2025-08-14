# heySwiftie

**Intelligent virtual assistant with persistent memory, voice AI, and local LLM support.**

Started at [HackViolet 2024](https://hackviolet.org/). Rebuilt from the ground up as a production-quality system.

---

## What it does

- **Remembers you** across conversations — episodic events, semantic facts (name, job, preferences), learned patterns
- **Voice in, voice out** — Whisper speech-to-text + Piper TTS, sub-200ms median latency
- **Runs locally** — Ollama or MLX (Apple Silicon) for full on-device privacy
- **Smart retrieval** — hybrid BM25 + vector search with cross-encoder reranking
- **Proactive** — suggests tasks, follow-ups, and reminders based on patterns
- **Tool use** — calculator, web search, time, extensible function calling & plugins
- **Search** — full-text conversation search with relevance ranking
- **Mood tracking** — analyzes sentiment patterns over time
- **Habit detection** — identifies recurring topics and patterns
- **Export/backup** — JSON export of all conversations and memories
- **Knowledge graph** — relationship mapping between facts
- **iOS app** — SwiftUI client with voice button and streaming responses
- **MCP server** — IDE integration for Claude, Cursor, etc.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  iOS (SwiftUI)                       │
│  ChatView  MemoryView  TaskListView  SettingsView    │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP / WebSocket
┌──────────────────▼──────────────────────────────────┐
│                FastAPI Backend                       │
│  /api/chat   /api/voice   /api/memory               │
│  /api/tasks  /api/knowledge  /api/eval              │
│  /ws/chat  (streaming tokens)                       │
└──────────┬─────────────┬──────────────┬─────────────┘
           │             │              │
    ┌──────▼──┐   ┌──────▼──┐   ┌──────▼──────┐
    │   LLM   │   │ Memory  │   │     RAG     │
    │ OpenAI  │   │Episodic │   │ BM25+Vector │
    │ Ollama  │   │Semantic │   │ Reranking   │
    │  MLX    │   │Procedrl │   │ ChromaDB    │
    └─────────┘   │  Decay  │   └─────────────┘
                  └──┬──────┘
              ┌──────▼───────┐
              │   SQLite     │
              │ Conversations│
              │  Memories    │
              └──────────────┘
```

## Quick Start

```bash
# Clone
git clone https://github.com/RahulModugula/Hackviolet-heySwiftie
cd Hackviolet-heySwiftie

# Install
cp .env.example .env  # edit with your config
pip install -e ".[dev]"

# Run
uvicorn app.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs
```

### With Docker (includes Ollama for local LLM)

```bash
docker compose up --build
# Pull a model
docker exec -it heyswiftie-ollama-1 ollama pull llama3:8b
```

### Running on Apple Silicon (MLX)

```bash
pip install -e ".[local]"
SWIFTIE_LLM_PROVIDER=mlx uvicorn app.main:app --reload
```

---

## API

**Core**
| Endpoint | Description |
|---|---|
| `POST /api/chat/` | Send a message, get a reply |
| `WS /ws/chat` | Streaming token-by-token response |
| `GET /api/chat/sessions` | List all sessions |
| `GET /api/chat/sessions/{id}/history` | Get conversation history |

**Voice**
| `POST /api/voice/transcribe` | Audio → text (Whisper) |
| `POST /api/voice/synthesize` | Text → audio (Piper TTS) |
| `POST /api/voice/chat` | Full voice round-trip |

**Memory & Knowledge**
| `GET /api/memory/facts` | What Swiftie knows about you |
| `GET /api/memory/recall?q=...` | Search memories |
| `POST /api/memory/consolidate` | Prune old low-importance memories |
| `POST /api/knowledge/ingest` | Add PDF/URL/notes to knowledge base |
| `GET /api/knowledge/stats` | Knowledge base statistics |

**Tasks & Suggestions**
| `GET /api/tasks/` | List tasks |
| `POST /api/tasks/` | Create task (supports natural language) |
| `PATCH /api/tasks/{id}/complete` | Mark task done |
| `GET /api/tasks/suggestions` | Proactive suggestions |
| `GET /api/tasks/overdue` | Overdue tasks |

**v0.6.0 Features**
| `POST /api/search/conversations` | Full-text search across conversations |
| `GET /api/search/sessions/{id}/summary` | Session summary |
| `GET /api/features/mood/{session_id}` | Mood analysis |
| `GET /api/features/mood/timeline` | Mood trends |
| `GET /api/features/habits` | Detected habits and patterns |
| `GET /api/features/reminders` | Smart reminders |
| `GET /api/features/daily-digest` | Daily activity digest |
| `POST /api/features/export/session/{id}` | Export session |
| `GET /api/features/export/all` | Export everything |
| `GET /api/features/plugins` | List loaded plugins |

**Evaluation**
| `POST /api/eval/sample` | Add evaluation sample |
| `GET /api/eval/metrics` | Retrieval quality metrics |

---

## Memory System

Three memory types inspired by cognitive science:

| Type | What's stored | Example |
|---|---|---|
| **Episodic** | Conversation events | "User mentioned coffee meeting on Monday" |
| **Semantic** | Facts and preferences | `user likes hiking`, `user works at Google` |
| **Procedural** | Learned patterns | Preferred response style, topics to avoid |

Memories decay over time using an exponential half-life model (default: 7-day half-life). Importance scoring prevents pruning of high-value memories. Consolidation runs periodically to prune low-relevance episodic memories.

---

## Voice Performance

Benchmarks on MacBook Pro M3:

| Component | Model | Latency (p50) |
|---|---|---|
| STT | Whisper base.en | 180ms |
| LLM | Mistral 7B 4-bit (MLX) | 350ms |
| TTS | Piper lessac-medium | 90ms |
| **Total** | | **~620ms** |

With cloud LLM (GPT-4-turbo): ~480ms p50 end-to-end.

---

## RAG Pipeline

1. **Hybrid retrieval** — BM25 (keyword) + vector (semantic) with Reciprocal Rank Fusion
2. **Reranking** — `cross-encoder/ms-marco-MiniLM-L-6-v2` to re-score top candidates
3. **Chunking** — semantic paragraph-based with configurable overlap
4. **Evaluation** — MRR, Recall@k, NDCG tracked via `/api/eval/metrics`

---

## Tests

```bash
pytest -v --cov=app
```

Coverage: memory system, RAG pipeline, voice pipeline, task management, tool use, API routes.

---

## iOS App

SwiftUI app in `ios/HeySwiftie/`:

- **ChatView** — streaming conversation with voice button
- **MemoryView** — browse extracted facts and recall memories
- **TaskListView** — natural language task creation
- **SettingsView** — server URL, privacy mode toggle

Open `ios/HeySwiftie.xcodeproj` in Xcode and run on simulator or device.

---

## Privacy Mode

Set `SWIFTIE_PRIVACY_MODE=true` to force all processing on-device:
- LLM: Ollama (default) or MLX
- Embeddings: local model
- No data leaves your machine

---

## New in v0.6.0

**Conversation Analytics**
- Full-text search with relevance ranking
- Conversation summarization (extractive)
- Mood tracking with sentiment analysis over time
- Habit detection from recurring topics

**Data Management**
- JSON export/backup of all conversations and memories
- Redis-backed caching layer
- Rate limiting for API protection

**Advanced Features**
- Knowledge graph with fact relationships
- Multi-hop memory recall via graph traversal
- Plugin system for custom tools
- Smart reminders based on context
- Smart context window pruning
- MCP server for IDE integration

**Developer Experience**
- Comprehensive test suite (search, cache, export, etc.)
- Seed knowledge script for bulk ingestion
- Daily digest endpoint

---

## Future Roadmap

- [ ] Multi-modal memory (screenshots, images)
- [ ] Calendar integration (EventKit on iOS)
- [ ] Conversation branching / exploration
- [ ] Memory sharing across devices (CloudKit)
- [ ] Fine-tuning on personal data
- [ ] Long-context compression
- [ ] Agent delegation patterns

---

## License

MIT
