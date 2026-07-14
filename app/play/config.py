from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    app_env: str = Field(default="local", alias="APP_ENV")
    app_name: str = Field(default="doping-chatbot", alias="APP_NAME")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

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