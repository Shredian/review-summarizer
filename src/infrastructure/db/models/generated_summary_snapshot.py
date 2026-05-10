from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from src.infrastructure.db.models.benchmark_product import BenchmarkProductDB
    from src.infrastructure.db.models.summary import SummaryDB


class GeneratedSummarySnapshotDB(Base):
    """Снимок summary нашего метода для benchmark товара."""

    __tablename__ = "generated_summary_snapshots"

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
    method_name: Mapped[str] = mapped_column(String(100), nullable=False)
    method_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("summaries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    text_overall: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_pros: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_cons: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_neutral: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_phrases_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)

    benchmark_product: Mapped[BenchmarkProductDB] = relationship(
        back_populates="generated_summaries",
        lazy="selectin",
    )
    summary: Mapped[SummaryDB | None] = relationship(
        "SummaryDB",
        lazy="selectin",
        foreign_keys=[summary_id],
    )
