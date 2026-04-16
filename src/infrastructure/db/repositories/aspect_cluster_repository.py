from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.infrastructure.db.models.aspect_cluster import AspectClusterDB


class AspectClusterRepository:
    """Репозиторий для сохранения кластеров аспектов."""

    def __init__(self, session_factory: sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def create_many(self, clusters: Sequence[AspectClusterDB]) -> list[UUID]:
        if not clusters:
            return []

        async with self.session_factory() as session:
            session.add_all(list(clusters))
            await session.commit()
            return [cluster.id for cluster in clusters]

    async def list_by_summary(self, summary_id: UUID, limit: int = 500) -> list[AspectClusterDB]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(AspectClusterDB)
                .where(AspectClusterDB.summary_id == summary_id)
                .order_by(AspectClusterDB.importance_score.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
