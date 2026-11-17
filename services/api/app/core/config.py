import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    app_env: str = os.getenv("APP_ENV", "development")
    app_base_url: str = os.getenv("APP_BASE_URL", "http://localhost:3000")
    api_base_url: str = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    
    # Database: Supports SQLite (for dev/testing) or PostgreSQL/PostGIS
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./fixproof_dev.db")
    
    # JWT Authentication
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "fixproof-civic-pilot-super-secret-key-32bytes-minimum")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24  # 24 hours
    
    # Storage
    object_storage_driver: str = os.getenv("OBJECT_STORAGE_DRIVER", "local")
    object_storage_local_path: str = os.getenv("OBJECT_STORAGE_LOCAL_PATH", "./storage")
    
    # AI Worker
    ai_worker_enabled: bool = os.getenv("AI_WORKER_ENABLED", "false").lower() == "true"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
