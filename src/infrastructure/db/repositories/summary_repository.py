from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.domain.models.summary import Summary
from src.infrastructure.db.models.summary import SummaryDB
from src.infrastructure.db.repositories.exceptions import NotFound


class SummaryRepository:
    """Репозиторий для работы с результатами суммаризации в БД."""

    def __init__(self, session_factory: sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def create(self, summary: Summary) -> UUID:
        """Создает суммаризацию в БД."""
        async with self.session_factory() as session:
            summary_db = summary.to_sql_model()
            session.add(summary_db)
            await session.commit()
            return summary_db.id

    async def get(self, summary_id: UUID) -> Summary:
        """Возвращает суммаризацию по ID."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(SummaryDB).where(SummaryDB.id == summary_id)
            )
            summary_db = result.scalar_one_or_none()
            if not summary_db:
                raise NotFound(f"Суммаризация с ID {summary_id} не найдена")
            return Summary.from_sql_model(summary_db)

    async def get_optional(self, summary_id: UUID) -> Optional[Summary]:
        """Возвращает суммаризацию по ID или None, если не найдена."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(SummaryDB).where(SummaryDB.id == summary_id)
            )
            summary_db = result.scalar_one_or_none()
            if not summary_db:
                return None
            return Summary.from_sql_model(summary_db)

    async def list(self, limit: int = 100, offset: int = 0) -> List[Summary]:
        """Возвращает список суммаризаций с пагинацией."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(SummaryDB)
                .order_by(SummaryDB.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            summaries_db = result.scalars().all()
            return [Summary.from_sql_model(s) for s in summaries_db]

    async def list_by_product(
        self,
        product_id: UUID,
        limit: int = 100,
        offset: int = 0,
        method: Optional[str] = None,
    ) -> List[Summary]:
        """Возвращает список суммаризаций по продукту."""
        async with self.session_factory() as session:
            query = select(SummaryDB).where(SummaryDB.product_id == product_id)
            
            if method:
                query = query.where(SummaryDB.method == method)
            
            query = query.order_by(SummaryDB.created_at.desc()).limit(limit).offset(offset)
            
            result = await session.execute(query)
            summaries_db = result.scalars().all()
            return [Summary.from_sql_model(s) for s in summaries_db]

    async def get_latest_by_product(
        self,
        product_id: UUID,
        method: Optional[str] = None,
    ) -> Optional[Summary]:
        """Возвращает последнюю суммаризацию по продукту."""
        async with self.session_factory() as session:
            query = select(SummaryDB).where(SummaryDB.product_id == product_id)
            
            if method:
                query = query.where(SummaryDB.method == method)
            
            query = query.order_by(SummaryDB.created_at.desc()).limit(1)
            
            result = await session.execute(query)
            summary_db = result.scalar_one_or_none()
            if not summary_db:
                return None
            return Summary.from_sql_model(summary_db)

    async def count_by_product(self, product_id: UUID) -> int:
        """Возвращает количество суммаризаций по продукту."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(func.count(SummaryDB.id)).where(SummaryDB.product_id == product_id)
            )
            return result.scalar_one()

    async def delete(self, summary_id: UUID) -> None:
        """Удаляет суммаризацию из БД."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(SummaryDB).where(SummaryDB.id == summary_id)
            )
            summary_db = result.scalar_one_or_none()
            if not summary_db:
                raise NotFound(f"Суммаризация с ID {summary_id} не найдена")
            
            await session.delete(summary_db)
            await session.commit()

    async def count(self) -> int:
        """Возвращает общее количество суммаризаций."""
        async with self.session_factory() as session:
            result = await session.execute(select(func.count(SummaryDB.id)))
            return result.scalar_one()
