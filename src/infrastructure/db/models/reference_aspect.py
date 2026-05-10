from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from src.infrastructure.db.models.reference_evidence import ReferenceEvidenceDB
    from src.infrastructure.db.models.reference_ledger import ReferenceLedgerDB


class ReferenceAspectDB(Base):
    """Аспект в reference ledger."""

    __tablename__ = "reference_aspects"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ledger_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("reference_ledgers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    aspect_name: Mapped[str] = mapped_column(String(255), nullable=False)
    salience_weight: Mapped[float] = mapped_column(Float, nullable=False)
    expected_polarity: Mapped[str] = mapped_column(String(32), nullable=False)
    polarity_distribution_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    rare_but_important: Mapped[bool] = mapped_column(Boolean, nullable=False)
    aliases_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)

    ledger: Mapped[ReferenceLedgerDB] = relationship(
        back_populates="aspects",
        lazy="selectin",
    )
    evidences: Mapped[list[ReferenceEvidenceDB]] = relationship(
        back_populates="reference_aspect",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
