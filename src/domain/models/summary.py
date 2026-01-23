from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.infrastructure.db.models.summary import SummaryDB


class KeyPhraseItem(BaseModel):
    phrase: str = Field(..., description="Словосочетание/фраза")
    sentiment: str = Field(..., description="positive | negative | neutral")
    count: int = Field(..., ge=0, description="Количество упоминаний")
    share: Optional[float] = Field(default=None, ge=0, le=1, description="Доля/процент встречаемости (0.18 = 18%)")


class Summary(BaseModel):
    id: Optional[UUID] = Field(default=None, description="Уникальный идентификатор суммаризации")
    product_id: UUID = Field(..., description="ID продукта")
    
    # Метаданные генерации
    method: str = Field(..., description="Код метода суммаризации")
    method_version: Optional[str] = Field(default=None, description="Версия/ревизия метода")
    params: Dict[str, Any] = Field(default_factory=dict, description="Параметры запуска")
    created_at: datetime = Field(default_factory=datetime.now, description="Дата создания")
    
    # Входная статистика
    reviews_count: int = Field(..., ge=0, description="Количество отзывов на входе")
    rating_avg: Optional[float] = Field(default=None, description="Средний рейтинг")
    date_min: Optional[datetime] = Field(default=None, description="Дата самого раннего отзыва")
    date_max: Optional[datetime] = Field(default=None, description="Дата самого позднего отзыва")
    
    # Тексты результата (все опциональны — зависят от метода)
    text_overall: Optional[str] = Field(default=None, description="Один общий текст (единый обзор)")
    text_neutral: Optional[str] = Field(default=None, description="Нейтральное резюме")
    text_pros: Optional[str] = Field(default=None, description="Обобщённые плюсы")
    text_cons: Optional[str] = Field(default=None, description="Обобщённые минусы")
    
    # Ключевые фразы
    key_phrases: Optional[List[KeyPhraseItem]] = Field(default=None, description="Ключевые фразы")

    def has_structured_summary(self) -> bool:
        """Проверяет, есть ли структурированный результат (pros/cons/neutral)."""
        return any([self.text_neutral, self.text_pros, self.text_cons])

    def has_overall_summary(self) -> bool:
        """Проверяет, есть ли общий текст суммаризации."""
        return self.text_overall is not None

    def has_key_phrases(self) -> bool:
        """Проверяет, есть ли ключевые фразы."""
        return self.key_phrases is not None and len(self.key_phrases) > 0

    @classmethod
    def from_sql_model(cls, summary_db: "SummaryDB") -> "Summary":
        """Конвертация из ORM модели в доменную модель."""
        data = {
            "id": summary_db.id,
            "product_id": summary_db.product_id,
            "method": summary_db.method,
            "method_version": summary_db.method_version,
            "params": summary_db.params or {},
            "created_at": summary_db.created_at,
            "reviews_count": summary_db.reviews_count,
            "rating_avg": summary_db.rating_avg,
            "date_min": summary_db.date_min,
            "date_max": summary_db.date_max,
            "text_overall": summary_db.text_overall,
            "text_neutral": summary_db.text_neutral,
            "text_pros": summary_db.text_pros,
            "text_cons": summary_db.text_cons,
            "key_phrases": [KeyPhraseItem(**kp) for kp in summary_db.key_phrases] if summary_db.key_phrases else None,
        }
        return cls(**data)

    def to_sql_model(self) -> "SummaryDB":
        """Конвертация доменной модели в ORM модель."""
        from src.infrastructure.db.models.summary import SummaryDB
        data = self.model_dump()
        if data.get("key_phrases"):
            data["key_phrases"] = [kp.model_dump() if isinstance(kp, KeyPhraseItem) else kp for kp in data["key_phrases"]]
        return SummaryDB(**data)
