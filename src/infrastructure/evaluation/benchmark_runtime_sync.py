from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.infrastructure.db.models.benchmark_product import BenchmarkProductDB
from src.infrastructure.db.models.benchmark_review import BenchmarkReviewDB
from src.infrastructure.db.models.product import ProductDB
from src.infrastructure.db.models.review import ReviewDB

from src.utils.logger import logger


async def sync_benchmark_to_main_tables(
    session_factory: sessionmaker[AsyncSession],
    product: BenchmarkProductDB,
    reviews: list[BenchmarkReviewDB],
) -> None:
    """Дублирует benchmark товар/отзывы в основные таблицы для AEG (FK на products/reviews)."""
    now = datetime.now(UTC)
    async with session_factory() as session:
        await session.execute(delete(ReviewDB).where(ReviewDB.product_id == product.id))
        await session.merge(
            ProductDB(
                id=product.id,
                name=product.product_title[:255],
                description=(product.product_url or "")[:10000] if product.product_url else None,
                created_at=now,
                updated_at=now,
            )
        )
        for br in reviews:
            await session.merge(
                ReviewDB(
                    id=br.id,
                    product_id=product.id,
                    user_id=None,
                    source=product.platform_name[:50],
                    url=br.source_url,
                    rating=br.rating,
                    title=br.title,
                    comment=br.comment,
                    plus=br.plus,
                    minus=br.minus,
                    review_date=br.review_date,
                    created_at=now,
                )
            )
        await session.commit()
    logger.debug("Синхронизирован benchmark {} в products/reviews", product.id)
