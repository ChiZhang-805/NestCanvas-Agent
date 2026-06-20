from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    app_name: str = "NestCanvas Agent API"
    api_prefix: str = "/api"
    database_url: str = Field(
        default=f"sqlite:///{ROOT_DIR / 'storage' / 'nestcanvas.db'}",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    storage_dir: Path = Field(default=ROOT_DIR / "storage", alias="STORAGE_DIR")
    sync_jobs: bool = Field(default=True, alias="SYNC_JOBS")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model_text: str = Field(default="gpt-5.5", alias="OPENAI_MODEL_TEXT")
    openai_model_fast: str = Field(default="gpt-5.4-mini", alias="OPENAI_MODEL_FAST")
    openai_image_model: str = Field(default="gpt-image-2", alias="OPENAI_IMAGE_MODEL")

    cors_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            "http://localhost:3010",
            "http://127.0.0.1:3010",
            "http://localhost:3011",
            "http://127.0.0.1:3011",
        ],
        alias="CORS_ORIGINS",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: list[str] | str) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.storage_dir.is_absolute():
        settings.storage_dir = (ROOT_DIR / settings.storage_dir).resolve()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    return settings
