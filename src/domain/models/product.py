from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.infrastructure.db.models.product import ProductDB


class Product(BaseModel):
    id: Optional[UUID] = Field(default=None, description="Уникальный идентификатор продукта")
    name: str = Field(..., max_length=255, description="Название продукта")
    description: Optional[str] = Field(default=None, description="Краткое описание/заметка")
    created_at: datetime = Field(default_factory=datetime.now, description="Дата создания")
    updated_at: datetime = Field(default_factory=datetime.now, description="Дата обновления")

    def update(self, name: Optional[str] = None, description: Optional[str] = None) -> None:
        """Обновление данных продукта."""
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        self.updated_at = datetime.now()

    @classmethod
    def from_sql_model(cls, product_db: "ProductDB") -> "Product":
        """Конвертация из ORM модели в доменную модель."""
        return cls.model_validate(product_db, from_attributes=True)

    def to_sql_model(self) -> "ProductDB":
        """Конвертация доменной модели в ORM модель."""
        from src.infrastructure.db.models.product import ProductDB
        return ProductDB(**self.model_dump())
