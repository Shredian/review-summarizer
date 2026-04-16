import uuid
from datetime import UTC, datetime
from typing import Any, Dict

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.models.base import Base


class AspectClusterDB(Base):
    """Кластер канонических аспектов внутри одной суммаризации."""

    __tablename__ = "aspect_clusters"

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
    summary_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("summaries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    aspect_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    aliases_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    total_mentions: Mapped[int] = mapped_column(Integer, nullable=False)
    positive_mentions: Mapped[int] = mapped_column(Integer, nullable=False)
    negative_mentions: Mapped[int] = mapped_column(Integer, nullable=False)
    neutral_mentions: Mapped[int] = mapped_column(Integer, nullable=False)
    mixed_mentions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    importance_score: Mapped[float] = mapped_column(Float, nullable=False)
    prevalence_score: Mapped[float] = mapped_column(Float, nullable=False)
    polarity_balance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rarity_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
    )
