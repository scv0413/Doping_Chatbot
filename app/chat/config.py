from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    app_env: str = Field(default="local", alias="APP_ENV")
    app_name: str = Field(default="doping-chatbot", alias="APP_NAME")

    api_auth_enabled: bool = Field(default=False, alias="API_AUTH_ENABLED")
    api_key_roles: str = Field(default="", alias="API_KEY_ROLES")
    api_rate_limit_enabled: bool = Field(default=False, alias="API_RATE_LIMIT_ENABLED")
    api_rate_limit_requests: int = Field(default=30, alias="API_RATE_LIMIT_REQUESTS")
    api_rate_limit_window_seconds: int = Field(default=60, alias="API_RATE_LIMIT_WINDOW_SECONDS")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")

    embedding_provider: str = Field(default="openai", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    chroma_collection_name: str = Field(
        default="doping_chunks_openai_small",
        alias="CHROMA_COLLECTION_NAME",
    )

    langsmith_tracing: bool = Field(default=False, alias="LANGSMITH_TRACING")
    langsmith_api_key: str | None = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="doping-chatbot", alias="LANGSMITH_PROJECT")

    raw_data_dir: Path = Field(default=Path("data/raw"), alias="RAW_DATA_DIR")
    processed_data_dir: Path = Field(default=Path("data/processed"), alias="PROCESSED_DATA_DIR")
    index_dir: Path = Field(default=Path("data/indexes"), alias="INDEX_DIR")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
