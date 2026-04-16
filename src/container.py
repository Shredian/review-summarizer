from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.utils.config import CONFIG

from src.infrastructure.db.repositories.product_repository import ProductRepository
from src.infrastructure.db.repositories.user_repository import UserRepository
from src.infrastructure.db.repositories.review_repository import ReviewRepository
from src.infrastructure.db.repositories.summary_repository import SummaryRepository
from src.infrastructure.db.repositories.aspect_mention_repository import AspectMentionRepository
from src.infrastructure.db.repositories.aspect_cluster_repository import AspectClusterRepository
from src.infrastructure.db.repositories.summary_evidence_repository import SummaryEvidenceRepository
from src.infrastructure.db.repositories.summary_plan_repository import SummaryPlanRepository

from src.infrastructure.clients.openai_client import OpenAIClient

from src.infrastructure.services.summarization.stub_method import StubSummarizationMethod
from src.infrastructure.services.summarization.llm_method import LLMSummarizationMethod
from src.infrastructure.services.summarization.aspect_method import AspectSummarizationMethod
from src.infrastructure.services.summarization.aspect_evidence_guided_method import (
    AspectEvidenceGuidedSummarizationMethod,
)

from src.domain.services.summarization_service import SummarizationService

from src.application.product_application import ProductApplication
from src.application.user_application import UserApplication
from src.application.review_application import ReviewApplication
from src.application.summary_application import SummaryApplication


class Container(containers.DeclarativeContainer):
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
    )

    summary_application = providers.Factory(
        SummaryApplication,
        summary_repository=summary_repository,
        review_repository=review_repository,
        summarization_service=summarization_service,
    )
