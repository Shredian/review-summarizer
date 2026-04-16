from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from src.domain.models.summary import Summary
from src.domain.services.summarization_service import SummarizationService
from src.infrastructure.db.repositories.review_repository import ReviewRepository
from src.infrastructure.db.repositories.summary_repository import SummaryRepository
from src.utils.logger import logger


class SummaryApplication:
    def __init__(
        self,
        summary_repository: SummaryRepository,
        review_repository: ReviewRepository,
        summarization_service: SummarizationService,
    ) -> None:
        self.summary_repository = summary_repository
        self.review_repository = review_repository
        self.summarization_service = summarization_service

    def get_available_methods(self) -> List[str]:
        """Получение списка доступных методов суммаризации."""
        return self.summarization_service.get_available_methods()

    def get_method_info(self, method_code: str) -> Dict[str, Any]:
        """Получение информации о методе суммаризации."""
        method = self.summarization_service.get_method(method_code)
        return method.get_info()

    async def generate(
        self,
        product_id: UUID,
        method_code: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Summary:
        """Генерация суммаризации отзывов по продукту."""
        start_time = datetime.now()
        logger.info(f"Начало генерации суммаризации для продукта {product_id}, метод: {method_code}")
        
        reviews = await self.review_repository.list_by_product(product_id)
        logger.info(f"Загружено {len(reviews)} отзывов")
        
        if not reviews:
            logger.warning(f"Нет отзывов для продукта {product_id}")
            raise ValueError(f"Нет отзывов для продукта {product_id}")
        
        summary = await self.summarization_service.summarize(
            product_id=str(product_id),
            reviews=reviews,
            method_code=method_code,
            params=params,
        )
        
        summary_id = await self.summary_repository.create(summary)
        summary.id = summary_id

        method = self.summarization_service.get_method(method_code)
        await method.persist_artifacts(summary)
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Суммаризация завершена за {duration:.2f} сек, ID: {summary_id}")
        
        return summary

    async def get(self, summary_id: UUID) -> Summary:
        """Получение суммаризации по ID."""
        return await self.summary_repository.get(summary_id)

    async def get_optional(self, summary_id: UUID) -> Optional[Summary]:
        """Получение суммаризации по ID или None, если не найдена."""
        return await self.summary_repository.get_optional(summary_id)

    async def list(self, limit: int = 100, offset: int = 0) -> List[Summary]:
        """Получение списка суммаризаций с пагинацией."""
        return await self.summary_repository.list(limit=limit, offset=offset)

    async def list_by_product(
        self,
        product_id: UUID,
        limit: int = 100,
        offset: int = 0,
        method: Optional[str] = None,
    ) -> List[Summary]:
        """Получение списка суммаризаций по продукту."""
        return await self.summary_repository.list_by_product(
            product_id=product_id,
            limit=limit,
            offset=offset,
            method=method,
        )

    async def get_latest_by_product(
        self,
        product_id: UUID,
        method: Optional[str] = None,
    ) -> Optional[Summary]:
        """Получение последней суммаризации по продукту."""
        return await self.summary_repository.get_latest_by_product(
            product_id=product_id,
            method=method,
        )

    async def count_by_product(self, product_id: UUID) -> int:
        """Получение количества суммаризаций по продукту."""
        return await self.summary_repository.count_by_product(product_id)

    async def delete(self, summary_id: UUID) -> None:
        """Удаление суммаризации."""
        await self.summary_repository.delete(summary_id)
        logger.info(f"Суммаризация {summary_id} удалена")

    async def count(self) -> int:
        """Получение общего количества суммаризаций."""
        return await self.summary_repository.count()
