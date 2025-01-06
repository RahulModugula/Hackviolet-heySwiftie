from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- LLM ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"
    llm_provider: str = "openai"  # openai | ollama | mlx
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3:8b"
    mlx_model: str = "mlx-community/Mistral-7B-Instruct-v0.3-4bit"

    # --- storage ---
    chroma_persist_dir: str = "./data/chroma"
    db_url: str = "sqlite:///./data/swiftie.db"
    redis_url: str = "redis://localhost:6379"

    # --- memory ---
    context_window: int = 20
    max_retrieval_docs: int = 5
    memory_decay_hours: float = 168.0  # 1 week half-life
    memory_importance_threshold: float = 0.3

    # --- voice ---
    whisper_model: str = "base.en"
    tts_model: str = "en_US-lessac-medium"
    tts_speaker: int = 0

    # --- rag ---
    chunk_size: int = 512
    chunk_overlap: int = 64
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    bm25_weight: float = 0.4
    vector_weight: float = 0.6

    # --- server ---
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    privacy_mode: bool = False  # force all-local

    model_config = {"env_prefix": "SWIFTIE_", "env_file": ".env"}


settings = Settings()
