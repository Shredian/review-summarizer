from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.infrastructure.db.models.review import ReviewDB


class Review(BaseModel):
    id: Optional[UUID] = Field(default=None, description="Уникальный идентификатор отзыва")
    product_id: UUID = Field(..., description="ID продукта")
    user_id: Optional[UUID] = Field(default=None, description="ID автора (если известен)")
    
    # Метаданные источника
    source: str = Field(..., description="Источник отзыва (ozon/wb/yandex/amazon и т.д.)")
    url: Optional[str] = Field(default=None, description="Ссылка на отзыв или страницу-источник")
    
    # Содержимое отзыва
    rating: Optional[float] = Field(default=None, ge=0, le=5, description="Рейтинг")
    title: Optional[str] = Field(default=None, description="Заголовок отзыва")
    comment: Optional[str] = Field(default=None, description="Текст отзыва")
    plus: Optional[str] = Field(default=None, description="Плюсы (достоинства)")
    minus: Optional[str] = Field(default=None, description="Минусы (недостатки)")
    
    # Даты
    review_date: Optional[datetime] = Field(default=None, description="Дата отзыва (если известна)")
    created_at: datetime = Field(default_factory=datetime.now, description="Дата добавления в БД")

    def get_full_text(self) -> str:
        """Возвращает полный текст отзыва для суммаризации."""
        parts = []
        if self.title:
            parts.append(self.title)
        if self.comment:
            parts.append(self.comment)
        if self.plus:
            parts.append(f"Плюсы: {self.plus}")
        if self.minus:
            parts.append(f"Минусы: {self.minus}")
        return "\n".join(parts)

    @classmethod
    def from_sql_model(cls, review_db: "ReviewDB") -> "Review":
        """Конвертация из ORM модели в доменную модель."""
        return cls.model_validate(review_db, from_attributes=True)

    def to_sql_model(self) -> "ReviewDB":
        """Конвертация доменной модели в ORM модель."""
        from src.infrastructure.db.models.review import ReviewDB
        return ReviewDB(**self.model_dump())
