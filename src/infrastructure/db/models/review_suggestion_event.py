import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import TIMESTAMP, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.models.base import Base


class ReviewSuggestionEventDB(Base):
    """События показа и взаимодействия с подсказками."""

    __tablename__ = "review_suggestion_events"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    context_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    field: Mapped[str] = mapped_column(String(20), nullable=False)
    current_text_before: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggestions: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    selected_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_text_after: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )
