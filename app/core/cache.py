"""Redis-backed caching layer for sessions and rate limiting."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RedisCache:
    """Simple Redis cache wrapper for sessions and rate limiting."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self._client = None
        self._redis_url = redis_url
        self._init_redis()

    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            import redis

            self._client = redis.from_url(self._redis_url, decode_responses=True)
            self._client.ping()
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning("Redis connection failed (%s), using in-memory fallback", e)
            self._memory_cache: dict[str, tuple[Any, float]] = {}

    def set(self, key: str, value: Any, ttl: int = 3600):
        """Set a key with optional TTL (seconds)."""
        if self._client:
            try:
                self._client.setex(key, ttl, json.dumps(value))
                return
            except Exception as e:
                logger.warning("Redis set failed: %s", e)

        # fallback: in-memory with TTL
        self._memory_cache[key] = (value, time.time() + ttl)

    def get(self, key: str) -> Any | None:
        """Get a key."""
        if self._client:
            try:
                val = self._client.get(key)
                return json.loads(val) if val else None
            except Exception as e:
                logger.warning("Redis get failed: %s", e)

        # fallback: in-memory
        if key in self._memory_cache:
            value, expiry = self._memory_cache[key]
            if time.time() < expiry:
                return value
            else:
                del self._memory_cache[key]
        return None

    def delete(self, key: str):
        """Delete a key."""
        if self._client:
            try:
                self._client.delete(key)
            except Exception:
                pass
        self._memory_cache.pop(key, None)

    def incr(self, key: str, amount: int = 1, ttl: int = 60) -> int:
        """Increment a counter (for rate limiting)."""
        if self._client:
            try:
                pipe = self._client.pipeline()
                pipe.incr(key, amount)
                pipe.expire(key, ttl)
                result = pipe.execute()
                return result[0]
            except Exception as e:
                logger.warning("Redis incr failed: %s", e)

        # fallback
        if key not in self._memory_cache:
            self._memory_cache[key] = (0, time.time() + ttl)
        value, expiry = self._memory_cache[key]
        if time.time() < expiry:
            self._memory_cache[key] = (value + amount, expiry)
            return value + amount
        else:
            self._memory_cache[key] = (amount, time.time() + ttl)
            return amount


class RateLimiter:
    """Simple rate limiter using Redis."""

    def __init__(self, cache: RedisCache, max_requests: int = 100, window_seconds: int = 60):
        self.cache = cache
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def is_allowed(self, client_id: str) -> bool:
        """Check if client is within rate limit."""
        key = f"rate_limit:{client_id}"
        count = self.cache.incr(key, 1, self.window_seconds)
        return count <= self.max_requests

    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client."""
        key = f"rate_limit:{client_id}"
        current = self.cache.get(key)
        return max(0, self.max_requests - (current or 0))
