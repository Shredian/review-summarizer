from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import TIMESTAMP, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from src.infrastructure.db.models.benchmark_product import BenchmarkProductDB


class ExternalSummarySnapshotDB(Base):
    """Публичный industry summary с платформы (black-box)."""

    __tablename__ = "external_summary_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    benchmark_product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("benchmark_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform_name: Mapped[str] = mapped_column(String(64), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    pros_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cons_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    highlights_json: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    raw_block_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    snapshot_timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    benchmark_product: Mapped[BenchmarkProductDB] = relationship(
        back_populates="external_summaries",
        lazy="selectin",
    )
