import uuid
from datetime import UTC, datetime

from sqlalchemy import Float, ForeignKey, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.models.base import Base


class AspectMentionDB(Base):
    """Упоминание аспекта в конкретном span отзыва."""

    __tablename__ = "aspect_mentions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    review_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    summary_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("summaries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    span_text: Mapped[str] = mapped_column(Text, nullable=False)
    section_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    aspect_raw: Mapped[str] = mapped_column(String(255), nullable=False)
    aspect_candidate: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sentiment_label: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    extractor_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    extractor_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
    )
