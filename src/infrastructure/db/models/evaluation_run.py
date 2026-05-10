from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import TIMESTAMP, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from src.infrastructure.db.models.evaluation_result import EvaluationResultDB


class EvaluationRunDB(Base):
    """Один прогон оценки по набору benchmark."""

    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    benchmark_set_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    run_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    config_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    results: Mapped[list[EvaluationResultDB]] = relationship(
        back_populates="evaluation_run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
