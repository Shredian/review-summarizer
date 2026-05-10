from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from src.infrastructure.db.models.benchmark_product import BenchmarkProductDB
    from src.infrastructure.db.models.evaluation_run import EvaluationRunDB


class EvaluationResultDB(Base):
    """Результаты метрик/judge по одной системе и одному товару в рамках run."""

    __tablename__ = "evaluation_results"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    benchmark_product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("benchmark_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    system_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    judge_scores_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    notes_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    evaluation_run: Mapped[EvaluationRunDB] = relationship(
        back_populates="results",
        lazy="selectin",
    )
    benchmark_product: Mapped[BenchmarkProductDB] = relationship(
        back_populates="evaluation_results",
        lazy="selectin",
    )
