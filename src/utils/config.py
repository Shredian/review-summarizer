from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Настройки приложения и внешних сервисов из переменных окружения (префикс APP_)."""

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/review_summarizer"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    streamlit_port: int = 8501

    log_level: str = "INFO"

    openai_api_key: str = ""
    openai_model: str = "gpt-5.4-mini"
    openai_model_mini: str = "gpt-5.4-nano"

    # Redis (кэш контекста подсказок + Streams для фоновых job)
    redis_url: str = "redis://localhost:6379/0"

    # Контекстные подсказки при написании отзыва
    review_suggestions_enabled: bool = True
    review_suggestions_context_ttl_seconds: int = 1800
    review_suggestions_max_suggestions: int = 3
    review_suggestions_min_prefix_len: int = 2
    review_suggestions_max_prefix_len: int = 40
    review_suggestions_embedding_model: str = "cointegrated/rubert-tiny2"
    review_suggestions_fallback_embedding_model: str = "intfloat/multilingual-e5-small"
    review_suggestions_use_onnx: bool = False
    review_suggestions_stream_name: str = "review_suggestions:profile_jobs"
    review_suggestions_stream_group: str = "review_suggestion_workers"
    review_suggestions_dlq_stream_name: str = "review_suggestions:profile_jobs:dlq"
    review_suggestions_max_job_attempts: int = 3
    review_suggestions_job_dedup_ttl_seconds: int = 600
    review_suggestions_pipeline_version: int = 1

    public_api_base_url: str = "http://localhost:8000"


CONFIG = AppConfig()
