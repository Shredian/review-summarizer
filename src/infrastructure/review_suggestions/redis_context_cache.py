from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis

from src.infrastructure.review_suggestions.redis_serde import dumps_bytes, loads_dict


class RedisSuggestionContextCache:
    """Кэш подготовленного контекста для online /suggest."""

    def __init__(
        self,
        redis: aioredis.Redis,
        ttl_seconds: int,
        key_prefix: str = "review_suggestions:context:",
    ) -> None:
        self._redis = redis
        self._ttl = ttl_seconds
        self._prefix = key_prefix

    def _key(self, context_id: str) -> str:
        return f"{self._prefix}{context_id}"

    async def get(self, context_id: str) -> dict[str, Any] | None:
        raw = await self._redis.get(self._key(context_id))
        if raw is None:
            return None
        return loads_dict(raw)

    async def set(self, context_id: str, payload: dict[str, Any]) -> None:
        await self._redis.set(self._key(context_id), dumps_bytes(payload), ex=self._ttl)
