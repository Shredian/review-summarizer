from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import sessionmaker

from src.infrastructure.db.models.evaluation_result import EvaluationResultDB
from src.infrastructure.db.models.evaluation_run import EvaluationRunDB
from src.infrastructure.db.repositories.exceptions import NotFound


class EvaluationRunRepository:
    """Сохранение прогонов оценки и строк результатов."""

    def __init__(self, session_factory: sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def create_run(self, run: EvaluationRunDB) -> UUID:
        async with self.session_factory() as session:
            session.add(run)
            await session.commit()
            await session.refresh(run)
            return run.id

    async def add_results(self, results: list[EvaluationResultDB]) -> None:
        async with self.session_factory() as session:
            for row in results:
                session.add(row)
            await session.commit()

    async def get_run_deep(self, run_id: UUID) -> EvaluationRunDB:
        async with self.session_factory() as session:
            result = await session.execute(
                select(EvaluationRunDB)
                .options(selectinload(EvaluationRunDB.results))
                .where(EvaluationRunDB.id == run_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                raise NotFound(f"EvaluationRun {run_id} не найден")
            return row

    async def list_runs_for_set(self, benchmark_set_name: str, limit: int = 50) -> list[EvaluationRunDB]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(EvaluationRunDB)
                .where(EvaluationRunDB.benchmark_set_name == benchmark_set_name)
                .order_by(EvaluationRunDB.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
