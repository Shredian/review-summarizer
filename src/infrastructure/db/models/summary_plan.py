import uuid
from datetime import UTC, datetime
from typing import Any, Dict

from sqlalchemy import ForeignKey, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.models.base import Base


class SummaryPlanDB(Base):
    """Артефакт content planning для конкретной суммаризации."""

    __tablename__ = "summary_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    summary_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("summaries.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    selected_aspects_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    dropped_aspects_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    diagnostics_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    planner_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
    )
