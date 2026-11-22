import os
from pydantic_settings import BaseSettings
from typing import Optional

def _resolve_database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./fixproof_dev.db")
    # If Render internal PostgreSQL host is supplied outside Render, auto-map to external host
    if "dpg-" in url and ".render.com" not in url and not os.getenv("RENDER"):
        import re
        url = re.sub(r"@dpg-([a-zA-Z0-9]+)-a/", r"@dpg-\1-a.oregon-postgres.render.com/", url)
    return url

class Settings(BaseSettings):
    app_env: str = os.getenv("APP_ENV", "development")
    app_base_url: str = os.getenv("APP_BASE_URL", "http://localhost:3000")
    api_base_url: str = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    
    # Database: Supports SQLite (for dev/testing) or PostgreSQL/PostGIS
    database_url: str = _resolve_database_url()
    
    # JWT Authentication
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "fixproof-civic-pilot-super-secret-key-32bytes-minimum")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24  # 24 hours
    
    # Storage
    object_storage_driver: str = os.getenv("OBJECT_STORAGE_DRIVER", "local")
    object_storage_local_path: str = os.getenv("OBJECT_STORAGE_LOCAL_PATH", "./storage")
    
    # AI Worker & Roboflow 5-Model Suite
    ai_worker_enabled: bool = os.getenv("AI_WORKER_ENABLED", "false").lower() == "true"
    roboflow_api_key: Optional[str] = os.getenv("ROBOFLOW_API_KEY", "")
    roboflow_api_url: str = os.getenv("ROBOFLOW_API_URL", "https://serverless.roboflow.com")
    roboflow_model_garbage: str = os.getenv("ROBOFLOW_MODEL_GARBAGE", "garbage_detection-wvzwv-n8vsv/1")
    roboflow_model_road: str = os.getenv("ROBOFLOW_MODEL_ROAD", "road-damage-detection-fn0qh/1")
    roboflow_model_waterlogging: str = os.getenv("ROBOFLOW_MODEL_WATERLOGGING", "water-logging-a7zhi/1")
    roboflow_model_civic_1: str = os.getenv("ROBOFLOW_MODEL_CIVIC_1", "civic-issues-lroee/3")
    roboflow_model_civic_2: str = os.getenv("ROBOFLOW_MODEL_CIVIC_2", "civic-issues-nq7sy-bh8t3/1")

    # Reverse Geocoding & Mapping
    nominatim_user_agent: str = os.getenv("NOMINATIM_USER_AGENT", "GramaSeva-Belagavi-Pilot/1.0")
    google_maps_api_key: Optional[str] = os.getenv("GOOGLE_MAPS_API_KEY", "")
    google_maps_public_key: Optional[str] = os.getenv("NEXT_PUBLIC_GOOGLE_MAPS_API_KEY", "")

    # Gemini AI Integration
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
