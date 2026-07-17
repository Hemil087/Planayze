from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "Planalyze"
    VERSION: str = "0.1.0"
    ENV: str = "development"

    DATABASE_URL: str

    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "google/gemma-4-31b-it:free"
    OPENROUTER_CHAT_MODEL: str = "nvidia/nemotron-3-super-120b-a12b:free"
    CONSISTENCY_RUNS: int = 5
    CONSISTENCY_THRESHOLD: int = 3
    STORAGE_DIR: str = "/storage/plans"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        # Render gives postgres:// but SQLAlchemy needs postgresql+asyncpg://
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()