import redis.asyncio as aioredis
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.application.evaluation_application import EvaluationApplication
from src.application.product_application import ProductApplication
from src.application.review_application import ReviewApplication
from src.application.review_suggestions.invalidate_profiles import (
    ReviewSuggestionProfileInvalidationService,
)
from src.application.review_suggestions.review_suggestion_application import (
    ReviewSuggestionApplicationService,
)
from src.application.summary_application import SummaryApplication
from src.application.user_application import UserApplication
from src.domain.services.summarization_service import SummarizationService
from src.infrastructure.clients.openai_client import OpenAIClient
from src.infrastructure.db.repositories.aspect_cluster_repository import AspectClusterRepository
from src.infrastructure.db.repositories.aspect_mention_repository import AspectMentionRepository
from src.infrastructure.db.repositories.benchmark_catalog_repository import (
    BenchmarkCatalogRepository,
)
from src.infrastructure.db.repositories.evaluation_run_repository import EvaluationRunRepository
from src.infrastructure.db.repositories.product_repository import ProductRepository
from src.infrastructure.db.repositories.product_suggestion_profile_repository import (
    ProductSuggestionProfileRepository,
)
from src.infrastructure.db.repositories.reference_ledger_repository import ReferenceLedgerRepository
from src.infrastructure.db.repositories.review_repository import ReviewRepository
from src.infrastructure.db.repositories.review_suggestion_event_repository import (
    ReviewSuggestionEventRepository,
)
from src.infrastructure.db.repositories.summary_evidence_repository import SummaryEvidenceRepository
from src.infrastructure.db.repositories.summary_plan_repository import SummaryPlanRepository
from src.infrastructure.db.repositories.summary_repository import SummaryRepository
from src.infrastructure.db.repositories.user_repository import UserRepository
from src.infrastructure.db.repositories.user_suggestion_profile_repository import (
    UserSuggestionProfileRepository,
)
from src.infrastructure.review_suggestions.redis_context_cache import RedisSuggestionContextCache
from src.infrastructure.review_suggestions.redis_profile_job_queue import RedisProfileJobQueue
from src.infrastructure.services.summarization.aspect_evidence_guided_method import (
    AspectEvidenceGuidedSummarizationMethod,
)
from src.infrastructure.services.summarization.aspect_method import AspectSummarizationMethod
from src.infrastructure.services.summarization.llm_method import LLMSummarizationMethod
from src.infrastructure.services.summarization.stub_method import StubSummarizationMethod
from src.utils.config import CONFIG


class Container(containers.DeclarativeContainer):
    """Сборка зависимостей: async SQLAlchemy, Redis, репозитории, сервисы, application-слой."""

    config = providers.Factory(lambda: CONFIG)

    db_engine = providers.Singleton(
        create_async_engine,
        CONFIG.database_url,
        pool_size=20,
        max_overflow=10,
        echo=False,
    )

    db_session_factory = providers.Singleton(
        async_sessionmaker,
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    product_repository = providers.Factory(
        ProductRepository,
        session_factory=db_session_factory,
    )

    user_repository = providers.Factory(
        UserRepository,
        session_factory=db_session_factory,
    )

    review_repository = providers.Factory(
        ReviewRepository,
        session_factory=db_session_factory,
    )

    summary_repository = providers.Factory(
        SummaryRepository,
        session_factory=db_session_factory,
    )

    aspect_mention_repository = providers.Factory(
        AspectMentionRepository,
        session_factory=db_session_factory,
    )

    aspect_cluster_repository = providers.Factory(
        AspectClusterRepository,
        session_factory=db_session_factory,
    )

    summary_evidence_repository = providers.Factory(
        SummaryEvidenceRepository,
        session_factory=db_session_factory,
    )

    summary_plan_repository = providers.Factory(
        SummaryPlanRepository,
        session_factory=db_session_factory,
    )

    benchmark_catalog_repository = providers.Factory(
        BenchmarkCatalogRepository,
        session_factory=db_session_factory,
    )

    reference_ledger_repository = providers.Factory(
        ReferenceLedgerRepository,
        session_factory=db_session_factory,
    )

    evaluation_run_repository = providers.Factory(
        EvaluationRunRepository,
        session_factory=db_session_factory,
    )

    redis_client = providers.Singleton(
        aioredis.from_url,
        CONFIG.redis_url,
        decode_responses=False,
    )

    product_suggestion_profile_repository = providers.Factory(
        ProductSuggestionProfileRepository,
        session_factory=db_session_factory,
    )

    user_suggestion_profile_repository = providers.Factory(
        UserSuggestionProfileRepository,
        session_factory=db_session_factory,
    )

    review_suggestion_event_repository = providers.Factory(
        ReviewSuggestionEventRepository,
        session_factory=db_session_factory,
    )

    review_suggestion_job_queue = providers.Factory(
        RedisProfileJobQueue,
        redis=redis_client,
        stream_name=CONFIG.review_suggestions_stream_name,
        dlq_stream_name=CONFIG.review_suggestions_dlq_stream_name,
        consumer_group=CONFIG.review_suggestions_stream_group,
        dedup_ttl_seconds=CONFIG.review_suggestions_job_dedup_ttl_seconds,
    )

    review_suggestion_context_cache = providers.Factory(
        RedisSuggestionContextCache,
        redis=redis_client,
        ttl_seconds=CONFIG.review_suggestions_context_ttl_seconds,
    )

    review_suggestion_invalidation_service = providers.Factory(
        ReviewSuggestionProfileInvalidationService,
        product_profile_repository=product_suggestion_profile_repository,
        user_profile_repository=user_suggestion_profile_repository,
        job_queue=review_suggestion_job_queue,
    )

    review_suggestion_application = providers.Factory(
        ReviewSuggestionApplicationService,
        config=providers.Callable(lambda: CONFIG),
        review_repository=review_repository,
        product_profile_repository=product_suggestion_profile_repository,
        user_profile_repository=user_suggestion_profile_repository,
        event_repository=review_suggestion_event_repository,
        context_cache=review_suggestion_context_cache,
        job_queue=review_suggestion_job_queue,
    )

    openai_client = providers.Singleton(
        OpenAIClient,
        api_key=CONFIG.openai_api_key,
        model=CONFIG.openai_model,
        temperature=1.0,
    )

    openai_client_mini = providers.Singleton(
        OpenAIClient,
        api_key=CONFIG.openai_api_key,
        model=CONFIG.openai_model_mini,
        temperature=1.0,
    )

    stub_summarization_method = providers.Singleton(StubSummarizationMethod)

    llm_summarization_method = providers.Singleton(
        LLMSummarizationMethod,
        openai_client=openai_client,
        openai_client_mini=openai_client_mini,
    )

    aspect_summarization_method = providers.Singleton(
        AspectSummarizationMethod,
        openai_client=openai_client,
        openai_client_mini=openai_client_mini,
    )

    aspect_evidence_guided_summarization_method = providers.Singleton(
        AspectEvidenceGuidedSummarizationMethod,
        aspect_mention_repository=aspect_mention_repository,
        aspect_cluster_repository=aspect_cluster_repository,
        summary_evidence_repository=summary_evidence_repository,
        summary_plan_repository=summary_plan_repository,
        openai_client=openai_client_mini,
    )

    summarization_methods = providers.Dict(
        stub=stub_summarization_method,
        llm=llm_summarization_method,
        aspect=aspect_summarization_method,
        aspect_evidence_guided_v1=aspect_evidence_guided_summarization_method,
    )

    summarization_service = providers.Factory(
        SummarizationService,
        methods=summarization_methods,
    )

    product_application = providers.Factory(
        ProductApplication,
        product_repository=product_repository,
    )

    user_application = providers.Factory(
        UserApplication,
        user_repository=user_repository,
    )

    review_application = providers.Factory(
        ReviewApplication,
        review_repository=review_repository,
        suggestion_invalidation=review_suggestion_invalidation_service,
    )

    summary_application = providers.Factory(
        SummaryApplication,
        summary_repository=summary_repository,
        review_repository=review_repository,
        summarization_service=summarization_service,
    )

    evaluation_application = providers.Factory(
        EvaluationApplication,
        session_factory=db_session_factory,
        benchmark_catalog_repository=benchmark_catalog_repository,
        reference_ledger_repository=reference_ledger_repository,
        evaluation_run_repository=evaluation_run_repository,
        summarization_service=summarization_service,
        summary_repository=summary_repository,
        summary_plan_repository=summary_plan_repository,
        openai_client=openai_client_mini,
    )
