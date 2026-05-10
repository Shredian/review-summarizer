from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, sessionmaker

from src.infrastructure.db.models.benchmark_product import BenchmarkProductDB
from src.infrastructure.db.models.benchmark_review import BenchmarkReviewDB
from src.infrastructure.db.models.external_summary_snapshot import ExternalSummarySnapshotDB
from src.infrastructure.db.models.generated_summary_snapshot import GeneratedSummarySnapshotDB
from src.infrastructure.db.repositories.exceptions import NotFound


class BenchmarkCatalogRepository:
    """Benchmark товары, отзывы и снимки summary."""

    def __init__(self, session_factory: sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def add_benchmark_product(self, row: BenchmarkProductDB) -> UUID:
        async with self.session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row.id

    async def add_benchmark_review(self, row: BenchmarkReviewDB) -> UUID:
        async with self.session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row.id

    async def add_external_snapshot(self, row: ExternalSummarySnapshotDB) -> UUID:
        async with self.session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row.id

    async def add_generated_snapshot(self, row: GeneratedSummarySnapshotDB) -> UUID:
        async with self.session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row.id

    async def upsert_benchmark_bundle(
        self,
        product: BenchmarkProductDB,
        reviews: list[BenchmarkReviewDB],
        external: ExternalSummarySnapshotDB | None,
    ) -> UUID:
        async with self.session_factory() as session:
            session.add(product)
            await session.flush()
            for r in reviews:
                r.benchmark_product_id = product.id
                session.add(r)
            if external is not None:
                external.benchmark_product_id = product.id
                session.add(external)
            await session.commit()
            await session.refresh(product)
            return product.id

    async def get_product(self, product_id: UUID) -> BenchmarkProductDB:
        async with self.session_factory() as session:
            result = await session.execute(
                select(BenchmarkProductDB).where(BenchmarkProductDB.id == product_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                raise NotFound(f"BenchmarkProduct {product_id} не найден")
            return row

    async def get_product_deep(self, product_id: UUID) -> BenchmarkProductDB:
        async with self.session_factory() as session:
            result = await session.execute(
                select(BenchmarkProductDB)
                .options(
                    selectinload(BenchmarkProductDB.reviews),
                    selectinload(BenchmarkProductDB.external_summaries),
                    selectinload(BenchmarkProductDB.generated_summaries),
                )
                .where(BenchmarkProductDB.id == product_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                raise NotFound(f"BenchmarkProduct {product_id} не найден")
            return row

    async def list_products_by_set(self, benchmark_set_name: str) -> list[BenchmarkProductDB]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(BenchmarkProductDB)
                .where(BenchmarkProductDB.benchmark_set_name == benchmark_set_name)
                .order_by(BenchmarkProductDB.platform_name, BenchmarkProductDB.product_title)
            )
            return list(result.scalars().all())

    async def list_products_by_set_deep(
        self, benchmark_set_name: str, *, limit: int | None = None
    ) -> list[BenchmarkProductDB]:
        async with self.session_factory() as session:
            stmt = (
                select(BenchmarkProductDB)
                .options(
                    selectinload(BenchmarkProductDB.reviews),
                    selectinload(BenchmarkProductDB.external_summaries),
                    selectinload(BenchmarkProductDB.generated_summaries),
                )
                .where(BenchmarkProductDB.benchmark_set_name == benchmark_set_name)
                .order_by(BenchmarkProductDB.platform_name, BenchmarkProductDB.product_title)
            )
            if limit is not None:
                stmt = stmt.limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_benchmark_sets_overview(self) -> list[tuple[str, int]]:
        """Имена наборов и число товаров — один лёгкий запрос без reviews."""
        async with self.session_factory() as session:
            q = (
                select(BenchmarkProductDB.benchmark_set_name, func.count(BenchmarkProductDB.id))
                .group_by(BenchmarkProductDB.benchmark_set_name)
                .order_by(BenchmarkProductDB.benchmark_set_name)
            )
            result = await session.execute(q)
            return [(str(row[0]), int(row[1])) for row in result.all()]
