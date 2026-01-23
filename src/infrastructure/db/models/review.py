import uuid
from datetime import datetime, UTC
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Float, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from src.infrastructure.db.models.product import ProductDB
    from src.infrastructure.db.models.user import UserDB


class ReviewDB(Base):
    """ORM модель для таблицы reviews (отзывы)."""
    
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    
    # Foreign keys
    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Метаданные источника
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Содержимое отзыва
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    plus: Mapped[str | None] = mapped_column(Text, nullable=True)
    minus: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Даты
    review_date: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    product: Mapped["ProductDB"] = relationship(
        back_populates="reviews",
    )
    user: Mapped["UserDB | None"] = relationship(
        back_populates="reviews",
    )
