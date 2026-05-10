"""Consumer Redis Streams: построение product/user NLP-профилей для подсказок."""

from __future__ import annotations

import asyncio
import traceback
import uuid
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.review_suggestions.source_hash import (
    compute_product_source_hash,
    compute_user_source_hash,
)
from src.infrastructure.db.models.registry import Base  # noqa: F401
from src.infrastructure.db.repositories.product_suggestion_profile_repository import (
    ProductSuggestionProfileRepository,
)
from src.infrastructure.db.repositories.review_repository import ReviewRepository
from src.infrastructure.db.repositories.user_suggestion_profile_repository import (
    UserSuggestionProfileRepository,
)
from src.infrastructure.review_suggestions.profile_building.payloads import (
    build_product_profile_payload,
    build_user_profile_payload,
)
from src.infrastructure.review_suggestions.redis_profile_job_queue import (
    RedisProfileJobQueue,
    decode_stream_job_fields,
)
from src.utils.config import CONFIG
from src.utils.logger import logger

CONSUMER = f"worker-{uuid.uuid4().hex[:8]}"


async def _process_product_job(
    job: dict,
    *,
    review_repo: ReviewRepository,
    prof_repo: ProductSuggestionProfileRepository,
    max_attempts: int,
    queue: RedisProfileJobQueue,
) -> None:
    pid = UUID(str(job["product_id"]))
    reviews = await review_repo.list_by_product_unbounded(pid)
    new_hash = compute_product_source_hash(pid, reviews)
    row = await prof_repo.get_by_product_id(pid)
    if row is not None and row.status == "ready" and row.source_hash == new_hash:
        logger.info(f"review_suggestions_worker: product {pid} profile up-to-date, skip")
        return
    try:
        payload = build_product_profile_payload(
            pid,
            reviews,
            embedding_model=CONFIG.review_suggestions_embedding_model,
            pipeline_version=CONFIG.review_suggestions_pipeline_version,
        )
        meta = payload.get("metadata") or {}
        await prof_repo.upsert_ready(
            pid,
            source_hash=payload["source_hash"],
            reviews_count=int(meta.get("reviews_count") or len(reviews)),
            segments_count=int(meta.get("segments_count") or 0),
            profile_payload=payload,
        )
        logger.info(
            f"review_suggestions_worker: product {pid} rebuilt reviews={len(reviews)} "
            f"segments={meta.get('segments_count')}"
        )
    except Exception as e:
        await prof_repo.mark_status(pid, "failed", last_error=str(e))
        attempt = int(job.get("attempt") or 1)
        if attempt < max_attempts:
            await queue.enqueue_product_rebuild(
                pid, str(job.get("reason") or "retry"), attempt=attempt + 1, force=True
            )
        else:
            await queue.publish_to_dlq(job, error=str(e))
        raise


async def _process_user_job(
    job: dict,
    *,
    review_repo: ReviewRepository,
    prof_repo: UserSuggestionProfileRepository,
    max_attempts: int,
    queue: RedisProfileJobQueue,
) -> None:
    uid = UUID(str(job["user_id"]))
    reviews = await review_repo.list_by_user_unbounded(uid)
    new_hash = compute_user_source_hash(uid, reviews)
    row = await prof_repo.get_by_user_id(uid)
    if row is not None and row.status == "ready" and row.source_hash == new_hash:
        logger.info(f"review_suggestions_worker: user {uid} profile up-to-date, skip")
        return
    try:
        payload = build_user_profile_payload(
            uid,
            reviews,
            embedding_model=CONFIG.review_suggestions_embedding_model,
            pipeline_version=CONFIG.review_suggestions_pipeline_version,
        )
        meta = payload.get("metadata") or {}
        sh = compute_user_source_hash(uid, reviews)
        await prof_repo.upsert_ready(
            uid,
            source_hash=sh,
            reviews_count=int(meta.get("reviews_count") or len(reviews)),
            profile_payload=payload,
        )
        logger.info(f"review_suggestions_worker: user {uid} rebuilt reviews={len(reviews)}")
    except Exception as e:
        await prof_repo.mark_status(uid, "failed", last_error=str(e))
        attempt = int(job.get("attempt") or 1)
        if attempt < max_attempts:
            await queue.enqueue_user_rebuild(
                uid, str(job.get("reason") or "retry"), attempt=attempt + 1, force=True
            )
        else:
            await queue.publish_to_dlq(job, error=str(e))
        raise


async def run_worker() -> None:
    engine = create_async_engine(CONFIG.database_url, pool_size=5, max_overflow=2, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    review_repo = ReviewRepository(session_factory)
    prod_repo = ProductSuggestionProfileRepository(session_factory)
    user_repo = UserSuggestionProfileRepository(session_factory)

    redis = aioredis.from_url(CONFIG.redis_url, decode_responses=False)
    queue = RedisProfileJobQueue(
        redis=redis,
        stream_name=CONFIG.review_suggestions_stream_name,
        dlq_stream_name=CONFIG.review_suggestions_dlq_stream_name,
        consumer_group=CONFIG.review_suggestions_stream_group,
        dedup_ttl_seconds=CONFIG.review_suggestions_job_dedup_ttl_seconds,
    )
    await queue.ensure_streams()
    stream = CONFIG.review_suggestions_stream_name
    group = CONFIG.review_suggestions_stream_group
    logger.info(f"review_suggestions_worker: started consumer={CONSUMER}")

    while True:
        try:
            resp = await redis.xreadgroup(
                groupname=group,
                consumername=CONSUMER,
                streams={stream: ">"},
                count=5,
                block=5000,
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception(f"review_suggestions_worker: xreadgroup error: {e}")
            await asyncio.sleep(1)
            continue
        if not resp:
            continue
        for _skey, messages in resp:
            for msg_id, fields in messages:
                lock_pid: UUID | None = None
                lock_uid: UUID | None = None
                try:
                    job = decode_stream_job_fields(fields)
                    jt = job.get("job_type")
                    if jt == "rebuild_product_profile":
                        lock_pid = UUID(str(job["product_id"]))
                        await _process_product_job(
                            job,
                            review_repo=review_repo,
                            prof_repo=prod_repo,
                            max_attempts=CONFIG.review_suggestions_max_job_attempts,
                            queue=queue,
                        )
                    elif jt == "rebuild_user_profile":
                        lock_uid = UUID(str(job["user_id"]))
                        await _process_user_job(
                            job,
                            review_repo=review_repo,
                            prof_repo=user_repo,
                            max_attempts=CONFIG.review_suggestions_max_job_attempts,
                            queue=queue,
                        )
                    else:
                        logger.warning(f"review_suggestions_worker: unknown job {jt}")
                except Exception:
                    logger.error(
                        f"review_suggestions_worker: job failed id={msg_id}\n{traceback.format_exc()}"
                    )
                finally:
                    if lock_pid is not None:
                        await queue.release_product_lock(lock_pid)
                    if lock_uid is not None:
                        await queue.release_user_lock(lock_uid)
                    await redis.xack(stream, group, msg_id)


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
