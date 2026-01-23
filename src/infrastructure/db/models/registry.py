"""Регистрация всех ORM моделей для Alembic."""

from src.infrastructure.db.models.base import Base
from src.infrastructure.db.models.product import ProductDB
from src.infrastructure.db.models.user import UserDB
from src.infrastructure.db.models.review import ReviewDB
from src.infrastructure.db.models.summary import SummaryDB

__all__ = ["Base", "ProductDB", "UserDB", "ReviewDB", "SummaryDB"]
