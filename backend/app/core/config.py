from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import secrets


class Settings(BaseSettings):
    # App
    APP_NAME: str = "DocFlow"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except Exception:
                return [i.strip() for i in v.split(",")]
        return v

    # Database
    DATABASE_URL: str = "postgresql://docflow_user:docflow_pass@localhost:5432/docflow_db"

    # Postgres (used by Docker Compose — declare so pydantic doesn't reject them)
    POSTGRES_USER: str = "docflow"
    POSTGRES_PASSWORD: str = "docflow123"
    POSTGRES_DB: str = "docflow_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # File Storage
    STORAGE_BACKEND: str = "local"
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 50

    @property
    def MAX_FILE_SIZE_BYTES(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    # Allowed file types
    ALLOWED_EXTENSIONS: List[str] = [
        ".pdf", ".txt", ".docx", ".doc",
        ".png", ".jpg", ".jpeg", ".csv", ".xlsx"
    ]

    # Frontend (declare so pydantic ignores them gracefully)
    NEXT_PUBLIC_API_URL: str = "http://localhost:3000"
    NEXT_PUBLIC_APP_NAME: str = "DocFlow"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"   # ← KEY: ignore any extra env vars not in the model


settings = Settings()