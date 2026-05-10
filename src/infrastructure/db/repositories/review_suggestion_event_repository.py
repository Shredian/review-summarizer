import uuid as uuid_lib
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.infrastructure.db.models.review_suggestion_event import ReviewSuggestionEventDB


class ReviewSuggestionEventRepository:
    """Журнал событий подсказок (prepare, показ, клик и т.д.)."""

    def __init__(self, session_factory: sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def log_event(
        self,
        *,
        context_id: str,
        product_id: UUID,
        user_id: UUID | None,
        field: str,
        event_type: str,
        current_text_before: str | None = None,
        suggestions: Any | None = None,
        selected_suggestion: str | None = None,
        current_text_after: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UUID:
        from datetime import UTC, datetime

        evt = ReviewSuggestionEventDB(
            id=uuid_lib.uuid4(),
            context_id=context_id,
            user_id=user_id,
            product_id=product_id,
            field=field,
            current_text_before=current_text_before,
            suggestions=suggestions,
            event_type=event_type,
            selected_suggestion=selected_suggestion,
            current_text_after=current_text_after,
            metadata_=metadata,
            created_at=datetime.now(UTC),
        )
        async with self.session_factory() as session:
            session.add(evt)
            await session.commit()
            return evt.id
