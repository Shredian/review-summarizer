from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import sessionmaker

from src.infrastructure.db.models.reference_aspect import ReferenceAspectDB
from src.infrastructure.db.models.reference_evidence import ReferenceEvidenceDB
from src.infrastructure.db.models.reference_ledger import ReferenceLedgerDB
from src.infrastructure.db.repositories.exceptions import NotFound


class ReferenceLedgerRepository:
    """Reference ledger с аспектами и доказательствами."""

    def __init__(self, session_factory: sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def save_ledger_tree(
        self,
        ledger: ReferenceLedgerDB,
        aspects: list[ReferenceAspectDB],
        evidences_by_aspect: list[list[ReferenceEvidenceDB]],
    ) -> UUID:
        if len(aspects) != len(evidences_by_aspect):
            raise ValueError("aspects и evidences_by_aspect должны совпадать по длине")
        async with self.session_factory() as session:
            session.add(ledger)
            await session.flush()
            for aspect, evs in zip(aspects, evidences_by_aspect, strict=True):
                aspect.ledger_id = ledger.id
                session.add(aspect)
                await session.flush()
                for ev in evs:
                    ev.reference_aspect_id = aspect.id
                    session.add(ev)
            await session.commit()
            await session.refresh(ledger)
            return ledger.id

    async def get_latest_ledger_deep(self, benchmark_product_id: UUID) -> ReferenceLedgerDB | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(ReferenceLedgerDB)
                .options(
                    selectinload(ReferenceLedgerDB.aspects).selectinload(ReferenceAspectDB.evidences),
                )
                .where(ReferenceLedgerDB.benchmark_product_id == benchmark_product_id)
                .order_by(ReferenceLedgerDB.created_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def get_ledger_deep(self, ledger_id: UUID) -> ReferenceLedgerDB:
        async with self.session_factory() as session:
            result = await session.execute(
                select(ReferenceLedgerDB)
                .options(
                    selectinload(ReferenceLedgerDB.aspects).selectinload(ReferenceAspectDB.evidences),
                )
                .where(ReferenceLedgerDB.id == ledger_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                raise NotFound(f"ReferenceLedger {ledger_id} не найден")
            return row
