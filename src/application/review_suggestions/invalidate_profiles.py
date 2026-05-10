from __future__ import annotations

from src.domain.models.review import Review
from src.infrastructure.db.repositories.product_suggestion_profile_repository import (
    ProductSuggestionProfileRepository,
)
from src.infrastructure.db.repositories.user_suggestion_profile_repository import (
    UserSuggestionProfileRepository,
)
from src.infrastructure.review_suggestions.redis_profile_job_queue import RedisProfileJobQueue
from src.utils.logger import logger


class ReviewSuggestionProfileInvalidationService:
    """После нового отзыва помечает профили подсказок устаревшими и ставит job на пересборку."""

    def __init__(
        self,
        product_profile_repository: ProductSuggestionProfileRepository,
        user_profile_repository: UserSuggestionProfileRepository,
        job_queue: RedisProfileJobQueue | None,
    ) -> None:
        self._prod = product_profile_repository
        self._user = user_profile_repository
        self._queue = job_queue

    async def invalidate_for_review(self, review: Review) -> None:
        """Статусы профилей и постановка в очередь для product_id и user_id отзыва."""
        try:
            await self._prod.mark_status(review.product_id, "stale")
            if self._queue:
                await self._queue.ensure_streams()
                await self._queue.enqueue_product_rebuild(
                    review.product_id, "review_created", force=True
                )
            if review.user_id:
                await self._user.mark_status(review.user_id, "stale")
                if self._queue:
                    await self._queue.enqueue_user_rebuild(
                        review.user_id, "review_created", force=True
                    )
        except Exception as e:  # pragma: no cover
            logger.warning(f"review_suggestions: invalidate failed: {e}")
