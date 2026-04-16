"""Регистрация всех ORM моделей для Alembic."""

from src.infrastructure.db.models.base import Base
from src.infrastructure.db.models.product import ProductDB
from src.infrastructure.db.models.user import UserDB
from src.infrastructure.db.models.review import ReviewDB
from src.infrastructure.db.models.summary import SummaryDB
from src.infrastructure.db.models.aspect_mention import AspectMentionDB
from src.infrastructure.db.models.aspect_cluster import AspectClusterDB
from src.infrastructure.db.models.summary_evidence import SummaryEvidenceDB
from src.infrastructure.db.models.summary_plan import SummaryPlanDB

__all__ = [
    "Base",
    "ProductDB",
    "UserDB",
    "ReviewDB",
    "SummaryDB",
    "AspectMentionDB",
    "AspectClusterDB",
    "SummaryEvidenceDB",
    "SummaryPlanDB",
]
