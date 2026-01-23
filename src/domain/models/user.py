from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.infrastructure.db.models.user import UserDB


class User(BaseModel):
    id: Optional[UUID] = Field(default=None, description="Уникальный идентификатор пользователя")
    display_name: str = Field(..., max_length=255, description="Отображаемое имя пользователя")
    profile_url: Optional[str] = Field(default=None, description="URL профиля пользователя")
    created_at: datetime = Field(default_factory=datetime.now, description="Дата создания записи")

    def update(self, display_name: Optional[str] = None, profile_url: Optional[str] = None) -> None:
        """Обновление данных пользователя."""
        if display_name is not None:
            self.display_name = display_name
        if profile_url is not None:
            self.profile_url = profile_url

    @classmethod
    def from_sql_model(cls, user_db: "UserDB") -> "User":
        """Конвертация из ORM модели в доменную модель."""
        return cls.model_validate(user_db, from_attributes=True)

    def to_sql_model(self) -> "UserDB":
        """Конвертация доменной модели в ORM модель."""
        from src.infrastructure.db.models.user import UserDB
        return UserDB(**self.model_dump())
