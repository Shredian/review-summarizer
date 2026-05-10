from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.infrastructure.db.models.product_suggestion_profile import ProductSuggestionProfileDB


class ProductSuggestionProfileRepository:
    """Профиль подсказок по товару (payload + статус пересборки)."""

    def __init__(self, session_factory: sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def get_by_product_id(self, product_id: UUID) -> ProductSuggestionProfileDB | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(ProductSuggestionProfileDB).where(
                    ProductSuggestionProfileDB.product_id == product_id
                )
            )
            return result.scalar_one_or_none()

    async def upsert_ready(
        self,
        product_id: UUID,
        *,
        source_hash: str,
        reviews_count: int,
        segments_count: int,
        profile_payload: dict[str, Any],
        version: int = 1,
    ) -> None:
        now = datetime.now(UTC)
        async with self.session_factory() as session:
            result = await session.execute(
                select(ProductSuggestionProfileDB).where(
                    ProductSuggestionProfileDB.product_id == product_id
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                row = ProductSuggestionProfileDB(
                    product_id=product_id,
                    status="ready",
                    version=version,
                    reviews_count=reviews_count,
                    segments_count=segments_count,
                    source_hash=source_hash,
                    profile_payload=profile_payload,
                    last_error=None,
                    built_at=now,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.status = "ready"
                row.version = version
                row.reviews_count = reviews_count
                row.segments_count = segments_count
                row.source_hash = source_hash
                row.profile_payload = profile_payload
                row.last_error = None
                row.built_at = now
                row.updated_at = now
            await session.commit()

    async def mark_status(
        self,
        product_id: UUID,
        status: str,
        *,
        last_error: str | None = None,
    ) -> None:
        now = datetime.now(UTC)
        async with self.session_factory() as session:
            result = await session.execute(
                select(ProductSuggestionProfileDB).where(
                    ProductSuggestionProfileDB.product_id == product_id
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                row = ProductSuggestionProfileDB(
                    product_id=product_id,
                    status=status,
                    version=1,
                    reviews_count=0,
                    segments_count=0,
                    source_hash="",
                    profile_payload={},
                    last_error=last_error,
                    built_at=None,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.status = status
                row.last_error = last_error
                row.updated_at = now
            await session.commit()
