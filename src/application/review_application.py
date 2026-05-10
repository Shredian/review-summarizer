from __future__ import annotations

import builtins
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from src.domain.models.review import Review
from src.infrastructure.db.repositories.review_repository import ReviewRepository
from src.utils.logger import logger

if TYPE_CHECKING:
    from src.application.review_suggestions.invalidate_profiles import (
        ReviewSuggestionProfileInvalidationService,
    )


class ReviewApplication:
    """Отзывы: сохранение, выборки, статистика; при создании — инвалидация профилей подсказок."""

    def __init__(
        self,
        review_repository: ReviewRepository,
        suggestion_invalidation: ReviewSuggestionProfileInvalidationService | None = None,
    ) -> None:
        self.review_repository = review_repository
        self._suggestion_invalidation = suggestion_invalidation

    async def _invalidate_if_needed(self, review: Review) -> None:
        """Ставит в очередь пересборку профилей подсказок для товара и автора."""
        if self._suggestion_invalidation is None:
            return
        await self._suggestion_invalidation.invalidate_for_review(review)

    async def create(self, review: Review) -> UUID:
        logger.info(f"Создание отзыва для продукта {review.product_id}")
        review_id = await self.review_repository.create(review)
        logger.info(f"Отзыв создан с ID: {review_id}")
        saved = review.model_copy(update={"id": review_id})
        await self._invalidate_if_needed(saved)
        return review_id

    async def create_many(self, reviews: list[Review]) -> list[UUID]:
        logger.info(f"Создание {len(reviews)} отзывов")
        review_ids = await self.review_repository.create_many(reviews)
        logger.info(f"Создано {len(review_ids)} отзывов")
        for rev, rid in zip(reviews, review_ids, strict=False):
            saved = rev.model_copy(update={"id": rid})
            await self._invalidate_if_needed(saved)
        return review_ids

    async def get(self, review_id: UUID) -> Review:
        return await self.review_repository.get(review_id)

    async def get_optional(self, review_id: UUID) -> Review | None:
        return await self.review_repository.get_optional(review_id)

    async def list(self, limit: int = 100, offset: int = 0) -> list[Review]:
        return await self.review_repository.list(limit=limit, offset=offset)

    async def list_by_product(
        self,
        product_id: UUID,
        limit: int = 1000,
        offset: int = 0,
        source: str | None = None,
        rating_min: float | None = None,
        rating_max: float | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> builtins.list[Review]:
        return await self.review_repository.list_by_product(
            product_id=product_id,
            limit=limit,
            offset=offset,
            source=source,
            rating_min=rating_min,
            rating_max=rating_max,
            date_from=date_from,
            date_to=date_to,
        )

    async def count_by_product(self, product_id: UUID) -> int:
        return await self.review_repository.count_by_product(product_id)

    async def get_stats_by_product(self, product_id: UUID) -> dict:
        return await self.review_repository.get_stats_by_product(product_id)

    async def get_sources_by_product(self, product_id: UUID) -> builtins.list[str]:
        return await self.review_repository.get_sources_by_product(product_id)

    async def delete(self, review_id: UUID) -> None:
        await self.review_repository.delete(review_id)
        logger.info(f"Отзыв {review_id} удалён")

    async def count(self) -> int:
        return await self.review_repository.count()
