from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.domain.models.product import Product
from src.infrastructure.db.models.product import ProductDB
from src.infrastructure.db.models.review import ReviewDB
from src.infrastructure.db.repositories.exceptions import NotFound


class ProductRepository:
    """Репозиторий для работы с продуктами в БД."""

    def __init__(self, session_factory: sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def create(self, product: Product) -> UUID:
        """Создает продукт в БД."""
        async with self.session_factory() as session:
            product_db = product.to_sql_model()
            session.add(product_db)
            await session.commit()
            return product_db.id

    async def get(self, product_id: UUID) -> Product:
        """Возвращает продукт по ID."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(ProductDB).where(ProductDB.id == product_id)
            )
            product_db = result.scalar_one_or_none()
            if not product_db:
                raise NotFound(f"Продукт с ID {product_id} не найден")
            return Product.from_sql_model(product_db)

    async def get_optional(self, product_id: UUID) -> Optional[Product]:
        """Возвращает продукт по ID или None, если не найден."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(ProductDB).where(ProductDB.id == product_id)
            )
            product_db = result.scalar_one_or_none()
            if not product_db:
                return None
            return Product.from_sql_model(product_db)

    async def list(self, limit: int = 100, offset: int = 0) -> List[Product]:
        """Возвращает список продуктов с пагинацией."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(ProductDB)
                .order_by(ProductDB.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            products_db = result.scalars().all()
            return [Product.from_sql_model(p) for p in products_db]

    async def list_with_reviews_count(
        self, limit: int = 100, offset: int = 0
    ) -> List[tuple[Product, int]]:
        """Возвращает список продуктов с количеством отзывов."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(ProductDB, func.count(ReviewDB.id).label("reviews_count"))
                .outerjoin(ReviewDB, ProductDB.id == ReviewDB.product_id)
                .group_by(ProductDB.id)
                .order_by(ProductDB.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            rows = result.all()
            return [(Product.from_sql_model(row[0]), row[1]) for row in rows]

    async def update(self, product: Product) -> None:
        """Обновляет продукт в БД."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(ProductDB).where(ProductDB.id == product.id)
            )
            product_db = result.scalar_one_or_none()
            if not product_db:
                raise NotFound(f"Продукт с ID {product.id} не найден")
            
            product_db.name = product.name
            product_db.description = product.description
            product_db.updated_at = product.updated_at
            await session.commit()

    async def delete(self, product_id: UUID) -> None:
        """Удаляет продукт из БД."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(ProductDB).where(ProductDB.id == product_id)
            )
            product_db = result.scalar_one_or_none()
            if not product_db:
                raise NotFound(f"Продукт с ID {product_id} не найден")
            
            await session.delete(product_db)
            await session.commit()

    async def count(self) -> int:
        """Возвращает общее количество продуктов."""
        async with self.session_factory() as session:
            result = await session.execute(select(func.count(ProductDB.id)))
            return result.scalar_one()
