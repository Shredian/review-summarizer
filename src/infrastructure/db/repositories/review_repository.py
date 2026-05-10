import builtins
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.domain.models.review import Review
from src.infrastructure.db.models.review import ReviewDB
from src.infrastructure.db.repositories.exceptions import NotFound


class ReviewRepository:
    """Отзывы в БД; «unbounded»-выборки — для построения профилей подсказок."""

    def __init__(self, session_factory: sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def create(self, review: Review) -> UUID:
        async with self.session_factory() as session:
            review_db = review.to_sql_model()
            session.add(review_db)
            await session.commit()
            return review_db.id

    async def create_many(self, reviews: list[Review]) -> list[UUID]:
        async with self.session_factory() as session:
            reviews_db = [r.to_sql_model() for r in reviews]
            session.add_all(reviews_db)
            await session.commit()
            return [r.id for r in reviews_db]

    async def get(self, review_id: UUID) -> Review:
        async with self.session_factory() as session:
            result = await session.execute(select(ReviewDB).where(ReviewDB.id == review_id))
            review_db = result.scalar_one_or_none()
            if not review_db:
                raise NotFound(f"Отзыв с ID {review_id} не найден")
            return Review.from_sql_model(review_db)

    async def get_optional(self, review_id: UUID) -> Review | None:
        async with self.session_factory() as session:
            result = await session.execute(select(ReviewDB).where(ReviewDB.id == review_id))
            review_db = result.scalar_one_or_none()
            if not review_db:
                return None
            return Review.from_sql_model(review_db)

    async def list(self, limit: int = 100, offset: int = 0) -> list[Review]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(ReviewDB).order_by(ReviewDB.created_at.desc()).limit(limit).offset(offset)
            )
            reviews_db = result.scalars().all()
            return [Review.from_sql_model(r) for r in reviews_db]

    async def list_by_product(
        self,
        product_id: UUID,
        limit: int = 1000,
        offset: int = 0,
        source: str | None = None,
        rating_min: float | None = None,
        rating_max: float | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> builtins.list[Review]:
        async with self.session_factory() as session:
            query = select(ReviewDB).where(ReviewDB.product_id == product_id)

            if source:
                query = query.where(ReviewDB.source == source)
            if rating_min is not None:
                query = query.where(ReviewDB.rating >= rating_min)
            if rating_max is not None:
                query = query.where(ReviewDB.rating <= rating_max)
            if date_from:
                query = query.where(ReviewDB.review_date >= date_from)
            if date_to:
                query = query.where(ReviewDB.review_date <= date_to)

            query = (
                query.order_by(ReviewDB.review_date.desc().nullslast()).limit(limit).offset(offset)
            )

            result = await session.execute(query)
            reviews_db = result.scalars().all()
            return [Review.from_sql_model(r) for r in reviews_db]

    async def count_by_product(self, product_id: UUID) -> int:
        async with self.session_factory() as session:
            result = await session.execute(
                select(func.count(ReviewDB.id)).where(ReviewDB.product_id == product_id)
            )
            return result.scalar_one()

    async def get_stats_by_product(self, product_id: UUID) -> dict:
        async with self.session_factory() as session:
            result = await session.execute(
                select(
                    func.count(ReviewDB.id).label("count"),
                    func.avg(ReviewDB.rating).label("rating_avg"),
                    func.min(ReviewDB.review_date).label("date_min"),
                    func.max(ReviewDB.review_date).label("date_max"),
                ).where(ReviewDB.product_id == product_id)
            )
            row = result.one()
            return {
                "count": row.count,
                "rating_avg": float(row.rating_avg) if row.rating_avg else None,
                "date_min": row.date_min,
                "date_max": row.date_max,
            }

    async def get_sources_by_product(self, product_id: UUID) -> builtins.list[str]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(ReviewDB.source).where(ReviewDB.product_id == product_id).distinct()
            )
            return [row[0] for row in result.all()]

    async def update(self, review: Review) -> None:
        async with self.session_factory() as session:
            result = await session.execute(select(ReviewDB).where(ReviewDB.id == review.id))
            review_db = result.scalar_one_or_none()
            if not review_db:
                raise NotFound(f"Отзыв с ID {review.id} не найден")

            review_db.rating = review.rating
            review_db.title = review.title
            review_db.comment = review.comment
            review_db.plus = review.plus
            review_db.minus = review.minus
            review_db.review_date = review.review_date
            await session.commit()

    async def delete(self, review_id: UUID) -> None:
        async with self.session_factory() as session:
            result = await session.execute(select(ReviewDB).where(ReviewDB.id == review_id))
            review_db = result.scalar_one_or_none()
            if not review_db:
                raise NotFound(f"Отзыв с ID {review_id} не найден")

            await session.delete(review_db)
            await session.commit()

    async def count(self) -> int:
        async with self.session_factory() as session:
            result = await session.execute(select(func.count(ReviewDB.id)))
            return result.scalar_one()

    async def list_by_product_unbounded(
        self,
        product_id: UUID,
        limit: int = 50_000,
    ) -> builtins.list[Review]:
        """Выборка до `limit` отзывов товара для хеша источника / NLP-профиля."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(ReviewDB)
                .where(ReviewDB.product_id == product_id)
                .order_by(ReviewDB.created_at.asc())
                .limit(limit)
            )
            reviews_db = result.scalars().all()
            return [Review.from_sql_model(r) for r in reviews_db]

    async def list_by_user_unbounded(
        self,
        user_id: UUID,
        limit: int = 50_000,
    ) -> builtins.list[Review]:
        """Выборка до `limit` отзывов пользователя для профиля стиля подсказок."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(ReviewDB)
                .where(ReviewDB.user_id == user_id)
                .order_by(ReviewDB.created_at.asc())
                .limit(limit)
            )
            reviews_db = result.scalars().all()
            return [Review.from_sql_model(r) for r in reviews_db]
