from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

import redis.asyncio as aioredis

from src.infrastructure.review_suggestions.redis_serde import (
    decode_stream_payload_fields,
    dumps_bytes,
)

ProfileJobType = Literal["rebuild_product_profile", "rebuild_user_profile"]


class RedisProfileJobQueue:
    """Очередь фоновых задач (Redis Streams) + dedup lock."""

    def __init__(
        self,
        redis: aioredis.Redis,
        stream_name: str,
        dlq_stream_name: str,
        consumer_group: str,
        dedup_ttl_seconds: int,
    ) -> None:
        self._redis = redis
        self._stream = stream_name
        self._dlq = dlq_stream_name
        self._group = consumer_group
        self._dedup_ttl = dedup_ttl_seconds

    async def ensure_streams(self) -> None:
        try:
            await self._redis.xgroup_create(
                self._stream,
                self._group,
                id="0",
                mkstream=True,
            )
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    def _product_lock(self, product_id: UUID) -> str:
        return f"review_suggestions:job_lock:product:{product_id}"

    def _user_lock(self, user_id: UUID) -> str:
        return f"review_suggestions:job_lock:user:{user_id}"

    async def try_acquire_product_lock(self, product_id: UUID) -> bool:
        ok = await self._redis.set(
            self._product_lock(product_id),
            "1",
            nx=True,
            ex=self._dedup_ttl,
        )
        return bool(ok)

    async def try_acquire_user_lock(self, user_id: UUID) -> bool:
        ok = await self._redis.set(
            self._user_lock(user_id),
            "1",
            nx=True,
            ex=self._dedup_ttl,
        )
        return bool(ok)

    async def release_product_lock(self, product_id: UUID) -> None:
        await self._redis.delete(self._product_lock(product_id))

    async def release_user_lock(self, user_id: UUID) -> None:
        await self._redis.delete(self._user_lock(user_id))

    async def enqueue_product_rebuild(
        self,
        product_id: UUID,
        reason: str,
        attempt: int = 1,
        *,
        force: bool = False,
    ) -> bool:
        if not force:
            acquired = await self.try_acquire_product_lock(product_id)
            if not acquired:
                return False
        job: dict[str, Any] = {
            "job_type": "rebuild_product_profile",
            "product_id": str(product_id),
            "reason": reason,
            "requested_at": datetime.now(UTC).isoformat(),
            "attempt": attempt,
        }
        await self._redis.xadd(self._stream, {"payload": dumps_bytes(job).decode("utf-8")})
        return True

    async def enqueue_user_rebuild(
        self,
        user_id: UUID,
        reason: str,
        attempt: int = 1,
        *,
        force: bool = False,
    ) -> bool:
        if not force:
            acquired = await self.try_acquire_user_lock(user_id)
            if not acquired:
                return False
        job: dict[str, Any] = {
            "job_type": "rebuild_user_profile",
            "user_id": str(user_id),
            "reason": reason,
            "requested_at": datetime.now(UTC).isoformat(),
            "attempt": attempt,
        }
        await self._redis.xadd(self._stream, {"payload": dumps_bytes(job).decode("utf-8")})
        return True

    async def publish_to_dlq(self, job: dict[str, Any], error: str) -> None:
        payload = dict(job)
        payload["_dlq_error"] = error
        payload["_dlq_at"] = datetime.now(UTC).isoformat()
        await self._redis.xadd(self._dlq, {"payload": dumps_bytes(payload).decode("utf-8")})


def decode_stream_job_fields(fields: dict[Any, Any]) -> dict[str, Any]:
    return decode_stream_payload_fields(fields)
