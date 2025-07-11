# Installation Guide

## Quick Start

### Prerequisites
- Python 3.11+
- pip
- Optional: Docker & Docker Compose

### Local Installation

```bash
git clone https://github.com/RahulModugula/heyswiftie
cd heyswiftie

# Install with development dependencies
pip install -e ".[dev,voice]"

# Set up environment
cp .env.example .env
# Edit .env with your OpenAI API key or Ollama settings

# Run server
make run
# → http://localhost:8000/docs
```

### With Docker

```bash
docker compose up --build
```

This includes:
- FastAPI server on port 8000
- Ollama for local LLM on port 11434
- Redis cache on port 6379
- SQLite database at `data/swiftie.db`

### Apple Silicon (MLX)

```bash
pip install -e ".[dev,local]"
SWIFTIE_LLM_PROVIDER=mlx make run
```

## Configuration

See `.env.example` for all settings:

```env
# LLM Provider
SWIFTIE_LLM_PROVIDER=openai  # openai | ollama | mlx
SWIFTIE_OPENAI_API_KEY=sk-...
SWIFTIE_OLLAMA_BASE_URL=http://localhost:11434
SWIFTIE_OLLAMA_MODEL=llama3:8b

# Memory & Context
SWIFTIE_CONTEXT_WINDOW=20
SWIFTIE_MEMORY_DECAY_HOURS=168

# Voice
SWIFTIE_WHISPER_MODEL=base.en
SWIFTIE_TTS_MODEL=en_US-lessac-medium

# RAG
SWIFTIE_BM25_WEIGHT=0.4
SWIFTIE_VECTOR_WEIGHT=0.6
SWIFTIE_RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

# Privacy
SWIFTIE_PRIVACY_MODE=false  # Force local LLM only
```

## Plugins

Add custom tools by creating Python files in `./plugins/`:

```python
# plugins/weather.py
from app.core.tools import ToolDefinition

async def weather_handler(location: str) -> str:
    return f"Weather for {location}: Sunny"

async def register_tools(tool_registry):
    tool_registry.register(ToolDefinition(
        name="weather",
        description="Get weather for a location",
        parameters={"type": "object", "properties": {"location": {"type": "string"}}},
        handler=weather_handler,
    ))

PLUGIN = type('Plugin', (), {
    'name': 'weather',
    'version': '0.1.0',
    'description': 'Weather tool',
    'register_tools': register_tools,
})()
```

Plugins auto-load on startup!

## Testing

```bash
make test           # Run all tests
make lint           # Check code style
make fmt            # Format code
```
