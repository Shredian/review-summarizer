from datetime import datetime
from typing import List, Optional
from uuid import UUID

from src.domain.models.review import Review
from src.infrastructure.db.repositories.review_repository import ReviewRepository
from src.utils.logger import logger


class ReviewApplication:
    def __init__(self, review_repository: ReviewRepository) -> None:
        self.review_repository = review_repository

    async def create(self, review: Review) -> UUID:
        """Создание отзыва."""
        logger.info(f"Создание отзыва для продукта {review.product_id}")
        review_id = await self.review_repository.create(review)
        logger.info(f"Отзыв создан с ID: {review_id}")
        return review_id

    async def create_many(self, reviews: List[Review]) -> List[UUID]:
        """Создание нескольких отзывов."""
        logger.info(f"Создание {len(reviews)} отзывов")
        review_ids = await self.review_repository.create_many(reviews)
        logger.info(f"Создано {len(review_ids)} отзывов")
        return review_ids

    async def get(self, review_id: UUID) -> Review:
        """Получение отзыва по ID."""
        return await self.review_repository.get(review_id)

    async def get_optional(self, review_id: UUID) -> Optional[Review]:
        """Получение отзыва по ID или None, если не найден."""
        return await self.review_repository.get_optional(review_id)

    async def list(self, limit: int = 100, offset: int = 0) -> List[Review]:
        """Получение списка отзывов с пагинацией."""
        return await self.review_repository.list(limit=limit, offset=offset)

    async def list_by_product(
        self,
        product_id: UUID,
        limit: int = 1000,
        offset: int = 0,
        source: Optional[str] = None,
        rating_min: Optional[float] = None,
        rating_max: Optional[float] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Review]:
        """Получение списка отзывов по продукту с фильтрацией."""
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
        """Получение количества отзывов по продукту."""
        return await self.review_repository.count_by_product(product_id)

    async def get_stats_by_product(self, product_id: UUID) -> dict:
        """Получение статистики отзывов по продукту."""
        return await self.review_repository.get_stats_by_product(product_id)

    async def get_sources_by_product(self, product_id: UUID) -> List[str]:
        """Получение списка уникальных источников отзывов по продукту."""
        return await self.review_repository.get_sources_by_product(product_id)

    async def delete(self, review_id: UUID) -> None:
        """Удаление отзыва."""
        await self.review_repository.delete(review_id)
        logger.info(f"Отзыв {review_id} удалён")

    async def count(self) -> int:
        """Получение общего количества отзывов."""
        return await self.review_repository.count()
