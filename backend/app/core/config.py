from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Planalyze"
    VERSION: str = "0.1.0"
    ENV: str = "development"

    # Database
    DATABASE_URL: str

    # Gemini
    GEMINI_API_KEY: str

    # Consistency filter
    CONSISTENCY_RUNS: int = 5
    CONSISTENCY_THRESHOLD: int = 3

    # Storage
    STORAGE_DIR: str = "/storage/plans"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()