from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from src.infrastructure.db.models.benchmark_product import BenchmarkProductDB
    from src.infrastructure.db.models.reference_evidence import ReferenceEvidenceDB


class BenchmarkReviewDB(Base):
    """Отзыв в benchmark snapshot."""

    __tablename__ = "benchmark_reviews"

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
    review_external_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    plus: Mapped[str | None] = mapped_column(Text, nullable=True)
    minus: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_date: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    benchmark_product: Mapped[BenchmarkProductDB] = relationship(
        back_populates="reviews",
        lazy="selectin",
    )
    reference_evidences: Mapped[list[ReferenceEvidenceDB]] = relationship(
        back_populates="review",
        lazy="selectin",
    )
