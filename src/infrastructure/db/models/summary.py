import uuid
from datetime import datetime, UTC
from typing import Any, Dict, List, TYPE_CHECKING

from sqlalchemy import String, Text, Float, Integer, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from src.infrastructure.db.models.product import ProductDB


class SummaryDB(Base):
    """ORM модель для таблицы summaries (результаты суммаризации)."""
    
    __tablename__ = "summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    
    # Foreign key
    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Метаданные генерации
    method: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    method_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    params: Mapped[Dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    
    # Входная статистика
    reviews_count: Mapped[int] = mapped_column(Integer, nullable=False)
    rating_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    date_min: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    date_max: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    
    # Тексты результата
    text_overall: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_neutral: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_pros: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_cons: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Ключевые фразы (JSONB массив)
    key_phrases: Mapped[List[Dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    product: Mapped["ProductDB"] = relationship(
        back_populates="summaries",
    )
