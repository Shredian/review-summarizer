import uuid
from datetime import datetime, UTC
from typing import List, TYPE_CHECKING

from sqlalchemy import String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from src.infrastructure.db.models.review import ReviewDB


class UserDB(Base):
    """ORM модель для таблицы users (авторы отзывов)."""
    
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    reviews: Mapped[List["ReviewDB"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )
