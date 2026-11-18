from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import os

from app.auth.router import router as auth_router
from app.localities.router import router as localities_router
from app.reports.router import router as reports_router
from app.staff.router import router as staff_router
from app.worker.router import router as worker_router
from app.public.router import router as public_router
from app.notifications.router import router as notifications_router
from app.ai.router import router as ai_router

app = FastAPI(
    title="FixProof Civic API",
    description="Multilingual civic complaint, infrastructure issue triage, work tracking, and repair verification platform.",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS setup
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    os.getenv("APP_BASE_URL", "http://localhost:3000"),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Sub-Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(localities_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(staff_router, prefix="/api/v1")
app.include_router(worker_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "name": "FixProof Civic API",
        "version": "0.1.0",
        "documentation": "/api/docs",
        "health": "/api/v1/health",
    }


@app.get("/api/v1/health", status_code=status.HTTP_200_OK)
def health_check():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "fixproof-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": os.getenv("APP_ENV", "development"),
        "ai_worker_enabled": os.getenv("AI_WORKER_ENABLED", "false").lower() == "true",
    }


@app.get("/api/v1/meta", status_code=status.HTTP_200_OK)
def pilot_metadata():
    return {
        "pilot_name": "FixProof Karnataka Gram Panchayat Pilot",
        "supported_locales": ["en", "kn", "hi"],
        "pilot_jurisdiction": {
            "state": "Karnataka",
            "district": "Mandya",
            "taluk": "Pandavapura",
            "default_gp": "Gowdanahalli Gram Panchayat",
        },
        "supported_categories": [
            {"code": "road_damage", "label_en": "Road Damage & Potholes"},
            {"code": "water_leak", "label_en": "Visible Water Leakage"},
            {"code": "garbage", "label_en": "Garbage & Litter Accumulation"},
            {"code": "drainage", "label_en": "Drainage & Waterlogging"},
            {"code": "streetlight", "label_en": "Streetlight Not Working"},
            {"code": "public_facility", "label_en": "Damaged Public Facility"},
            {"code": "other", "label_en": "Other Public Infrastructure Issue"},
        ],
        "lifecycle_statuses": [
            "DRAFT",
            "SUBMITTED",
            "UNDER_REVIEW",
            "ASSIGNED",
            "IN_PROGRESS",
            "REPAIR_REPORTED",
            "RESOLUTION_REVIEW",
            "RESOLVED",
            "NEEDS_INFORMATION",
            "REOPENED",
            "REJECTED",
        ],
    }
