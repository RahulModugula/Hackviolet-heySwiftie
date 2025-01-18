"""LLM provider abstraction - supports OpenAI, Ollama, and MLX."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int = 0
    finish_reason: str = "stop"


@dataclass
class StreamChunk:
    delta: str
    done: bool = False


class LLMProvider(ABC):
    """Base class for all LLM providers."""

    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse: ...

    async def stream(
        self,
        messages: list[dict],
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ):
        """Stream response token by token. Default falls back to generate."""
        resp = await self.generate(messages, system, temperature, max_tokens)
        yield StreamChunk(delta=resp.content, done=True)

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate(self, messages, system="", temperature=0.7, max_tokens=1024):
        full = []
        if system:
            full.append({"role": "system", "content": system})
        full.extend(messages)

        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=full,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = resp.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            model=self.model,
            tokens_used=resp.usage.total_tokens if resp.usage else 0,
            finish_reason=choice.finish_reason or "stop",
        )

    async def stream(self, messages, system="", temperature=0.7, max_tokens=1024):
        full = []
        if system:
            full.append({"role": "system", "content": system})
        full.extend(messages)

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=full,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield StreamChunk(delta=delta.content)
            if chunk.choices[0].finish_reason:
                yield StreamChunk(delta="", done=True)

    async def embed(self, text: str) -> list[float]:
        resp = await self.client.embeddings.create(model="text-embedding-3-small", input=text)
        return resp.data[0].embedding


class OllamaProvider(LLMProvider):
    """Local LLM via Ollama HTTP API."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3:8b"):
        import httpx

        self.base_url = base_url.rstrip("/")
        self.model = model
        self.http = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)

    async def generate(self, messages, system="", temperature=0.7, max_tokens=1024):
        full = []
        if system:
            full.append({"role": "system", "content": system})
        full.extend(messages)

        resp = await self.http.post(
            "/api/chat",
            json={
                "model": self.model,
                "messages": full,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return LLMResponse(
            content=data["message"]["content"],
            model=self.model,
            tokens_used=data.get("eval_count", 0),
        )

    async def stream(self, messages, system="", temperature=0.7, max_tokens=1024):
        import httpx
        full = []
        if system:
            full.append({"role": "system", "content": system})
        full.extend(messages)

        async with self.http.stream(
            "POST",
            "/api/chat",
            json={
                "model": self.model,
                "messages": full,
                "stream": True,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
        ) as resp:
            import json

            async for line in resp.aiter_lines():
                if not line:
                    continue
                data = json.loads(line)
                content = data.get("message", {}).get("content", "")
                done = data.get("done", False)
                if content:
                    yield StreamChunk(delta=content, done=done)
                if done:
                    yield StreamChunk(delta="", done=True)
                    break

    async def embed(self, text: str) -> list[float]:
        resp = await self.http.post(
            "/api/embeddings", json={"model": self.model, "prompt": text}
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


class MLXProvider(LLMProvider):
    """Apple Silicon local inference via MLX."""

    def __init__(self, model_name: str = "mlx-community/Mistral-7B-Instruct-v0.3-4bit"):
        self.model_name = model_name
        self._model = None
        self._tokenizer = None

    def _load(self):
        if self._model is not None:
            return
        try:
            from mlx_lm import load

            self._model, self._tokenizer = load(self.model_name)
            logger.info("MLX model loaded: %s", self.model_name)
        except ImportError:
            raise RuntimeError("mlx-lm not installed. pip install mlx-lm")

    async def generate(self, messages, system="", temperature=0.7, max_tokens=1024):
        import asyncio
        self._load()
        from mlx_lm import generate as mlx_generate

        prompt = self._format_messages(messages, system)
        text = await asyncio.to_thread(
            mlx_generate,
            self._model,
            self._tokenizer,
            prompt=prompt,
            max_tokens=max_tokens,
            temp=temperature,
        )
        return LLMResponse(content=text, model=self.model_name)

    async def embed(self, text: str) -> list[float]:
        import asyncio
        self._load()
        import numpy as np

        tokens = self._tokenizer.encode(text)
        import mlx.core as mx

        arr = mx.array([tokens])
        # use the model's embedding layer
        emb = self._model.model.embed_tokens(arr)
        vec = emb.mean(axis=1).squeeze()
        return await asyncio.to_thread(lambda: np.array(vec).tolist())

    def _format_messages(self, messages: list[dict], system: str) -> str:
        parts = []
        if system:
            parts.append(f"[INST] <<SYS>>\n{system}\n<</SYS>>\n\n")
        for m in messages:
            if m["role"] == "user":
                parts.append(f"[INST] {m['content']} [/INST]")
            else:
                parts.append(m["content"])
        return "\n".join(parts)


def get_provider(provider: str = "openai", **kwargs) -> LLMProvider:
    """Factory for LLM providers."""
    if provider == "openai":
        return OpenAIProvider(
            api_key=kwargs.get("api_key", ""),
            model=kwargs.get("model", "gpt-4-turbo-preview"),
        )
    elif provider == "ollama":
        return OllamaProvider(
            base_url=kwargs.get("base_url", "http://localhost:11434"),
            model=kwargs.get("model", "llama3:8b"),
        )
    elif provider == "mlx":
        return MLXProvider(model_name=kwargs.get("model", ""))
    raise ValueError(f"Unknown LLM provider: {provider}")
