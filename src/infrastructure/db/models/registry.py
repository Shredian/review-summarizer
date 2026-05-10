"""Регистрация всех ORM моделей для Alembic."""

from src.infrastructure.db.models.aspect_cluster import AspectClusterDB
from src.infrastructure.db.models.aspect_mention import AspectMentionDB
from src.infrastructure.db.models.base import Base
from src.infrastructure.db.models.benchmark_product import BenchmarkProductDB
from src.infrastructure.db.models.benchmark_review import BenchmarkReviewDB
from src.infrastructure.db.models.evaluation_result import EvaluationResultDB
from src.infrastructure.db.models.evaluation_run import EvaluationRunDB
from src.infrastructure.db.models.external_summary_snapshot import ExternalSummarySnapshotDB
from src.infrastructure.db.models.generated_summary_snapshot import GeneratedSummarySnapshotDB
from src.infrastructure.db.models.product import ProductDB
from src.infrastructure.db.models.product_suggestion_profile import ProductSuggestionProfileDB
from src.infrastructure.db.models.reference_aspect import ReferenceAspectDB
from src.infrastructure.db.models.reference_evidence import ReferenceEvidenceDB
from src.infrastructure.db.models.reference_ledger import ReferenceLedgerDB
from src.infrastructure.db.models.review import ReviewDB
from src.infrastructure.db.models.review_suggestion_event import ReviewSuggestionEventDB
from src.infrastructure.db.models.summary import SummaryDB
from src.infrastructure.db.models.summary_evidence import SummaryEvidenceDB
from src.infrastructure.db.models.summary_plan import SummaryPlanDB
from src.infrastructure.db.models.user import UserDB
from src.infrastructure.db.models.user_suggestion_profile import UserSuggestionProfileDB

__all__ = [
    "AspectClusterDB",
    "AspectMentionDB",
    "Base",
    "BenchmarkProductDB",
    "BenchmarkReviewDB",
    "EvaluationResultDB",
    "EvaluationRunDB",
    "ExternalSummarySnapshotDB",
    "GeneratedSummarySnapshotDB",
    "ProductDB",
    "ProductSuggestionProfileDB",
    "ReferenceAspectDB",
    "ReferenceEvidenceDB",
    "ReferenceLedgerDB",
    "ReviewDB",
    "ReviewSuggestionEventDB",
    "SummaryDB",
    "SummaryEvidenceDB",
    "SummaryPlanDB",
    "UserDB",
    "UserSuggestionProfileDB",
]
