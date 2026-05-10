from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from src.infrastructure.db.models.benchmark_review import BenchmarkReviewDB
    from src.infrastructure.db.models.reference_aspect import ReferenceAspectDB


class ReferenceEvidenceDB(Base):
    """Доказательство по аспекту в ledger."""

    __tablename__ = "reference_evidences"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    reference_aspect_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("reference_aspects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    review_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("benchmark_reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    section_type: Mapped[str] = mapped_column(String(32), nullable=False)
    polarity: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_strength: Mapped[float | None] = mapped_column(Float, nullable=True)

    reference_aspect: Mapped[ReferenceAspectDB] = relationship(
        back_populates="evidences",
        lazy="selectin",
    )
    review: Mapped[BenchmarkReviewDB] = relationship(
        back_populates="reference_evidences",
        lazy="selectin",
    )
