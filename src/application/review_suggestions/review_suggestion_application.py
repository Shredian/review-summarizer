from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.domain.review_suggestions.source_hash import (
    compute_product_source_hash,
    compute_user_source_hash,
)
from src.infrastructure.db.repositories.product_suggestion_profile_repository import (
    ProductSuggestionProfileRepository,
)
from src.infrastructure.db.repositories.review_repository import ReviewRepository
from src.infrastructure.db.repositories.review_suggestion_event_repository import (
    ReviewSuggestionEventRepository,
)
from src.infrastructure.db.repositories.user_suggestion_profile_repository import (
    UserSuggestionProfileRepository,
)
from src.infrastructure.review_suggestions.online.generators import merge_candidates
from src.infrastructure.review_suggestions.online.ranking import rank_candidates
from src.infrastructure.review_suggestions.online.safety_filter import SuggestionSafetyFilter
from src.infrastructure.review_suggestions.online.text_state import build_text_input_state
from src.infrastructure.review_suggestions.redis_context_cache import RedisSuggestionContextCache
from src.infrastructure.review_suggestions.redis_profile_job_queue import RedisProfileJobQueue
from src.utils.config import AppConfig
from src.utils.logger import logger


def _minimal_product_profile(product_id: UUID) -> dict[str, Any]:
    return {
        "product_id": str(product_id),
        "source_hash": "",
        "phrase_bank": [],
        "aspects": [],
        "ngram_index": {"lemma_contexts": {}, "surface_contexts": {}},
        "prefix_index": {},
        "generic_starters": [
            "в целом",
            "по ощущениям",
            "для ежедневного использования",
            "есть небольшие нюансы",
            "за свою цену",
        ],
        "metadata": {},
    }


def _minimal_user_profile(user_id: UUID) -> dict[str, Any]:
    return {
        "user_id": str(user_id),
        "common_phrases": [],
        "common_openers": [],
        "common_connectors": [],
        "avg_review_len_tokens": 0.0,
        "avg_sentence_len_tokens": 0.0,
        "punctuation_profile": {},
        "style_flags": {"short_practical": 0.0, "formal": 0.0, "emotional": 0.0},
        "metadata": {},
    }


class ReviewSuggestionApplicationService:
    """Онлайн-подсказки при наборе отзыва: контекст в Redis, кандидаты из профилей товара и пользователя."""

    def __init__(
        self,
        config: AppConfig,
        review_repository: ReviewRepository,
        product_profile_repository: ProductSuggestionProfileRepository,
        user_profile_repository: UserSuggestionProfileRepository,
        event_repository: ReviewSuggestionEventRepository,
        context_cache: RedisSuggestionContextCache | None,
        job_queue: RedisProfileJobQueue | None,
    ) -> None:
        self._config = config
        self._reviews = review_repository
        self._prod_prof = product_profile_repository
        self._user_prof = user_profile_repository
        self._events = event_repository
        self._cache = context_cache
        self._queue = job_queue

    async def prepare_context(
        self,
        *,
        product_id: UUID,
        user_id: UUID | None,
        rating: float | None,
        field: str,
    ) -> dict[str, Any]:
        """Собирает payload профилей, кладёт сессию в Redis, при необходимости ставит пересборку профилей."""
        if not self._config.review_suggestions_enabled:
            ctx_id = str(uuid.uuid4())
            return {
                "context_id": ctx_id,
                "status": "ready",
                "fallback_used": True,
                "profile_status": {
                    "product_profile": "pending",
                    "user_profile": "pending",
                },
            }

        reviews = await self._reviews.list_by_product_unbounded(product_id)
        current_ph = compute_product_source_hash(product_id, reviews)

        prod_row = await self._prod_prof.get_by_product_id(product_id)
        prod_ok = (
            prod_row is not None
            and prod_row.status == "ready"
            and prod_row.source_hash == current_ph
        )
        prod_payload = (
            dict(prod_row.profile_payload)
            if prod_row and prod_row.status == "ready"
            else _minimal_product_profile(product_id)
        )
        if not prod_ok and self._queue:
            try:
                await self._queue.ensure_streams()
                enq = await self._queue.enqueue_product_rebuild(
                    product_id,
                    "prepare_missing" if prod_row is None else "prepare_stale",
                )
                logger.info(f"review_suggestions: enqueue product rebuild {product_id} ok={enq}")
                if not enq:
                    logger.warning(
                        "review_suggestions: product rebuild not enqueued (dedup lock); "
                        "wait for worker or retry after TTL"
                    )
            except Exception as e:  # pragma: no cover
                logger.warning(f"review_suggestions: enqueue product failed: {e}")

        user_ok = True
        user_payload: dict[str, Any] | None = None
        current_uh = None
        if user_id is not None:
            ur = await self._reviews.list_by_user_unbounded(user_id)
            current_uh = compute_user_source_hash(user_id, ur)
            urow = await self._user_prof.get_by_user_id(user_id)
            user_ok = urow is not None and urow.status == "ready" and urow.source_hash == current_uh
            user_payload = (
                dict(urow.profile_payload)
                if urow and urow.status == "ready"
                else _minimal_user_profile(user_id)
            )
            if not user_ok and self._queue:
                try:
                    await self._queue.ensure_streams()
                    enq_u = await self._queue.enqueue_user_rebuild(
                        user_id,
                        "prepare_missing" if urow is None else "prepare_stale",
                    )
                    logger.info(f"review_suggestions: enqueue user rebuild {user_id} ok={enq_u}")
                    if not enq_u:
                        logger.warning(
                            "review_suggestions: user rebuild not enqueued (dedup lock); "
                            "wait for worker or retry after TTL"
                        )
                except Exception as e:  # pragma: no cover
                    logger.warning(f"review_suggestions: enqueue user failed: {e}")

        fallback_used = not prod_ok or (user_id is not None and not user_ok)
        status = "fallback" if fallback_used else "ready"

        ctx_id = str(uuid.uuid4())
        ctx = {
            "context_id": ctx_id,
            "product_id": str(product_id),
            "user_id": str(user_id) if user_id else None,
            "rating": rating,
            "field": field,
            "product_profile": prod_payload,
            "user_profile": user_payload,
            "fallback_used": fallback_used,
            "created_at": datetime.now(UTC).isoformat(),
        }

        if self._cache:
            try:
                await self._cache.set(ctx_id, ctx)
            except Exception as e:  # pragma: no cover
                logger.warning(f"review_suggestions: redis cache set failed: {e}")

        await self._events.log_event(
            context_id=ctx_id,
            product_id=product_id,
            user_id=user_id,
            field=field,
            event_type="prepared",
            metadata={"fallback_used": fallback_used},
        )

        return {
            "context_id": ctx_id,
            "status": status,
            "fallback_used": fallback_used,
            "profile_status": {
                "product_profile": "ready" if prod_ok else "pending",
                "user_profile": "ready" if user_id is None else ("ready" if user_ok else "pending"),
            },
        }

    async def suggest(
        self,
        *,
        context_id: str,
        current_text: str,
        cursor_position: int,
        field: str,
        limit: int = 3,
    ) -> dict[str, Any]:
        """Формирует ранжированный список подсказок по контексту из Redis."""
        t0 = time.perf_counter()
        if not self._config.review_suggestions_enabled or not self._cache:
            return {
                "context_id": context_id,
                "suggestions": [],
                "metadata": {"fallback_used": True, "latency_ms": 0},
            }
        try:
            ctx = await self._cache.get(context_id)
        except Exception as e:  # pragma: no cover
            logger.warning(f"review_suggestions: redis get failed: {e}")
            return {
                "context_id": context_id,
                "suggestions": [],
                "metadata": {"fallback_used": True, "latency_ms": 0},
            }
        if ctx is None:
            return {
                "context_id": context_id,
                "suggestions": [],
                "metadata": {"fallback_used": True, "latency_ms": 0},
            }

        rating = ctx.get("rating")
        if isinstance(rating, str):
            try:
                rating = float(rating)
            except ValueError:
                rating = None

        profile = ctx.get("product_profile") or _minimal_product_profile(
            UUID(str(ctx["product_id"]))
        )
        user_profile = ctx.get("user_profile")

        state = build_text_input_state(
            current_text,
            cursor_position,
            field=field,
            rating=rating if isinstance(rating, int | float) else None,
        )
        merged = merge_candidates(state, profile, user_profile)

        seen: set[str] = set()
        deduped = []
        for c in merged:
            k = (c.insert_text or c.text).strip().lower()
            if not k or k in seen:
                continue
            seen.add(k)
            deduped.append(c)
        filt = SuggestionSafetyFilter().filter(deduped, state)
        max_n = min(limit, self._config.review_suggestions_max_suggestions)
        ranked = rank_candidates(filt, state, max_n=max_n)
        lat = int((time.perf_counter() - t0) * 1000)
        sugg = []
        for c in ranked:
            sugg.append(
                {
                    "id": c.id,
                    "text": c.text,
                    "insert_text": c.insert_text,
                    "type": c.type,
                    "insert_mode": c.insert_mode,
                    "aspect_id": c.aspect_id,
                    "aspect_label": c.aspect_label,
                    "confidence": float(c.confidence),
                    "source": c.source,
                }
            )
        return {
            "context_id": context_id,
            "suggestions": sugg,
            "metadata": {
                "fallback_used": bool(ctx.get("fallback_used")),
                "latency_ms": lat,
            },
        }

    async def register_feedback(
        self,
        *,
        context_id: str,
        product_id: UUID,
        user_id: UUID | None,
        field: str,
        event_type: str,
        current_text_before: str | None = None,
        selected_suggestion: str | None = None,
        current_text_after: str | None = None,
        suggestions: Any | None = None,
    ) -> None:
        """Сохраняет событие показа/принятия подсказки для аналитики."""
        await self._events.log_event(
            context_id=context_id,
            product_id=product_id,
            user_id=user_id,
            field=field,
            event_type=event_type,
            current_text_before=current_text_before,
            suggestions=suggestions,
            selected_suggestion=selected_suggestion,
            current_text_after=current_text_after,
        )
