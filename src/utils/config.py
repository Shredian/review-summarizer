from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
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
    openai_model: str = "gpt-4.1"
    openai_model_mini: str = "gpt-4.1-mini"


CONFIG = AppConfig()
