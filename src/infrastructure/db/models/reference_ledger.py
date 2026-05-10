from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from src.infrastructure.db.models.benchmark_product import BenchmarkProductDB
    from src.infrastructure.db.models.reference_aspect import ReferenceAspectDB


class ReferenceLedgerDB(Base):
    """Review-derived reference ledger для benchmark товара."""

    __tablename__ = "reference_ledgers"

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
    reference_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    benchmark_product: Mapped[BenchmarkProductDB] = relationship(
        back_populates="reference_ledgers",
        lazy="selectin",
    )
    aspects: Mapped[list[ReferenceAspectDB]] = relationship(
        back_populates="ledger",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
