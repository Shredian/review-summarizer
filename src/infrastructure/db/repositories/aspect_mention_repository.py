from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.infrastructure.db.models.aspect_mention import AspectMentionDB


class AspectMentionRepository:
    """Репозиторий для сохранения упоминаний аспектов."""

    def __init__(self, session_factory: sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def create_many(self, mentions: Sequence[AspectMentionDB]) -> list[UUID]:
        if not mentions:
            return []

        async with self.session_factory() as session:
            session.add_all(list(mentions))
            await session.commit()
            return [mention.id for mention in mentions]

    async def list_by_summary(self, summary_id: UUID, limit: int = 5000) -> list[AspectMentionDB]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(AspectMentionDB)
                .where(AspectMentionDB.summary_id == summary_id)
                .order_by(AspectMentionDB.created_at.asc())
                .limit(limit)
            )
            return list(result.scalars().all())
