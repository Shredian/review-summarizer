from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.infrastructure.db.models.summary_evidence import SummaryEvidenceDB


class SummaryEvidenceRepository:
    """Репозиторий для сохранения evidence spans."""

    def __init__(self, session_factory: sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def create_many(self, evidence_items: Sequence[SummaryEvidenceDB]) -> list[UUID]:
        if not evidence_items:
            return []

        async with self.session_factory() as session:
            session.add_all(list(evidence_items))
            await session.commit()
            return [evidence.id for evidence in evidence_items]

    async def list_by_summary(self, summary_id: UUID, limit: int = 5000) -> list[SummaryEvidenceDB]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(SummaryEvidenceDB)
                .where(SummaryEvidenceDB.summary_id == summary_id)
                .order_by(SummaryEvidenceDB.evidence_rank.asc(), SummaryEvidenceDB.created_at.asc())
                .limit(limit)
            )
            return list(result.scalars().all())
