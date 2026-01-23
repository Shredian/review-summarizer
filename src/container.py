from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.utils.config import CONFIG

from src.infrastructure.db.repositories.product_repository import ProductRepository
from src.infrastructure.db.repositories.user_repository import UserRepository
from src.infrastructure.db.repositories.review_repository import ReviewRepository
from src.infrastructure.db.repositories.summary_repository import SummaryRepository

from src.infrastructure.clients.openai_client import OpenAIClient

from src.infrastructure.services.summarization.stub_method import StubSummarizationMethod
from src.infrastructure.services.summarization.llm_method import LLMSummarizationMethod

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

    summarization_methods = providers.Dict(
        stub=stub_summarization_method,
        llm=llm_summarization_method,
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
