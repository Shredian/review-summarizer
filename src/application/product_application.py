from typing import List, Optional
from uuid import UUID

from src.domain.models.product import Product
from src.infrastructure.db.repositories.product_repository import ProductRepository
from src.utils.logger import logger


class ProductApplication:
    def __init__(self, product_repository: ProductRepository) -> None:
        self.product_repository = product_repository

    async def create(self, product: Product) -> UUID:
        """Создание продукта."""
        logger.info(f"Создание продукта: {product.name}")
        product_id = await self.product_repository.create(product)
        logger.info(f"Продукт создан с ID: {product_id}")
        return product_id

    async def get(self, product_id: UUID) -> Product:
        """Получение продукта по ID."""
        return await self.product_repository.get(product_id)

    async def get_optional(self, product_id: UUID) -> Optional[Product]:
        """Получение продукта по ID или None, если не найден."""
        return await self.product_repository.get_optional(product_id)

    async def list(self, limit: int = 100, offset: int = 0) -> List[Product]:
        """Получение списка продуктов с пагинацией."""
        return await self.product_repository.list(limit=limit, offset=offset)

    async def list_with_reviews_count(
        self, limit: int = 100, offset: int = 0
    ) -> List[tuple[Product, int]]:
        """Получение списка продуктов с количеством отзывов."""
        return await self.product_repository.list_with_reviews_count(
            limit=limit, offset=offset
        )

    async def update(
        self,
        product_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Product:
        """Обновление продукта."""
        product = await self.product_repository.get(product_id)
        product.update(name=name, description=description)
        await self.product_repository.update(product)
        logger.info(f"Продукт {product_id} обновлён")
        return product

    async def delete(self, product_id: UUID) -> None:
        """Удаление продукта."""
        await self.product_repository.delete(product_id)
        logger.info(f"Продукт {product_id} удалён")

    async def count(self) -> int:
        """Получение общего количества продуктов."""
        return await self.product_repository.count()
