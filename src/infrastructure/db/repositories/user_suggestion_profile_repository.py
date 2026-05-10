from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.infrastructure.db.models.user_suggestion_profile import UserSuggestionProfileDB


class UserSuggestionProfileRepository:
    """Профиль стиля автора отзывов для персонализации подсказок."""

    def __init__(self, session_factory: sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def get_by_user_id(self, user_id: UUID) -> UserSuggestionProfileDB | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserSuggestionProfileDB).where(UserSuggestionProfileDB.user_id == user_id)
            )
            return result.scalar_one_or_none()

    async def upsert_ready(
        self,
        user_id: UUID,
        *,
        source_hash: str,
        reviews_count: int,
        profile_payload: dict[str, Any],
        version: int = 1,
    ) -> None:
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserSuggestionProfileDB).where(UserSuggestionProfileDB.user_id == user_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                row = UserSuggestionProfileDB(
                    user_id=user_id,
                    status="ready",
                    version=version,
                    reviews_count=reviews_count,
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
                row.source_hash = source_hash
                row.profile_payload = profile_payload
                row.last_error = None
                row.built_at = now
                row.updated_at = now
            await session.commit()

    async def mark_status(
        self,
        user_id: UUID,
        status: str,
        *,
        last_error: str | None = None,
    ) -> None:
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserSuggestionProfileDB).where(UserSuggestionProfileDB.user_id == user_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                row = UserSuggestionProfileDB(
                    user_id=user_id,
                    status=status,
                    version=1,
                    reviews_count=0,
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
