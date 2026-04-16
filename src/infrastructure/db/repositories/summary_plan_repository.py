from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.infrastructure.db.models.summary_plan import SummaryPlanDB


class SummaryPlanRepository:
    """Репозиторий для сохранения плана суммаризации."""

    def __init__(self, session_factory: sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def create(self, plan: SummaryPlanDB) -> UUID:
        async with self.session_factory() as session:
            session.add(plan)
            await session.commit()
            return plan.id

    async def get_by_summary(self, summary_id: UUID) -> SummaryPlanDB | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(SummaryPlanDB).where(SummaryPlanDB.summary_id == summary_id)
            )
            return result.scalar_one_or_none()
