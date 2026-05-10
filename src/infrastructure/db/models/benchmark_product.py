from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from src.infrastructure.db.models.benchmark_review import BenchmarkReviewDB
    from src.infrastructure.db.models.evaluation_result import EvaluationResultDB
    from src.infrastructure.db.models.external_summary_snapshot import ExternalSummarySnapshotDB
    from src.infrastructure.db.models.generated_summary_snapshot import GeneratedSummarySnapshotDB
    from src.infrastructure.db.models.reference_ledger import ReferenceLedgerDB


class BenchmarkProductDB(Base):
    """Товар в наборе benchmark (замороженный snapshot)."""

    __tablename__ = "benchmark_products"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    benchmark_set_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    platform_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_external_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    product_title: Mapped[str] = mapped_column(String(1024), nullable=False)
    product_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot_timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    category: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    reviews: Mapped[list[BenchmarkReviewDB]] = relationship(
        back_populates="benchmark_product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    external_summaries: Mapped[list[ExternalSummarySnapshotDB]] = relationship(
        back_populates="benchmark_product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    generated_summaries: Mapped[list[GeneratedSummarySnapshotDB]] = relationship(
        back_populates="benchmark_product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    reference_ledgers: Mapped[list[ReferenceLedgerDB]] = relationship(
        back_populates="benchmark_product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    evaluation_results: Mapped[list[EvaluationResultDB]] = relationship(
        back_populates="benchmark_product",
        lazy="selectin",
        passive_deletes=True,
    )
