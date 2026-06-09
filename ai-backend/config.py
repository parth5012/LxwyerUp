import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "LxwyerUp AI Backend"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Database Settings
    # Fallback to local SQLite for easy plug-and-play development, else PostgreSQL
    DATABASE_URL: str = "sqlite:///./lxwyerup.db"

    # Redis and Celery Settings
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Storage Settings
    STORAGE_DIR: str = "./storage"

    # LLM Settings (Gemini / Ollama / Local)
    GOOGLE_API_KEY: Optional[str] = ""
    OLLAMA_HOST: str = "http://localhost:11434"
    DEFAULT_LLM_MODEL: str = "gemini-1.5-flash"
    EMBEDDING_MODEL: str = "gemini-embedding-001"

    # LangSmith / Observability
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "LxwyerUp"

    # Path to the environment file
    ENV_PATH: str = ".env"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Instantiated singletons
settings = Settings()

# Ensure local storage directory exists
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_DIR, "evidence"), exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_DIR, "drafts"), exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_DIR, "screenshots"), exist_ok=True)
