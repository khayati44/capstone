from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Groq
    groq_api_key: str = "your_groq_api_key_here"
    groq_model: str = "llama-3.3-70b-versatile"

    # JWT
    secret_key: str = "change-me-in-production-must-be-at-least-32-chars!!"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Database
    database_url: str = "sqlite:////app/db/tax_deductions.db"

    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"

    # App
    app_env: str = "development"
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:8501"

    # Upload
    max_upload_size_mb: int = 10
    upload_dir: str = "./uploads"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
