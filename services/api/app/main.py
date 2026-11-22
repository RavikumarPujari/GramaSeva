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
from app.translations.router import router as translations_router
from app.assets.router import router as assets_router
from app.admin.router import router as admin_router
from app.citizen.router import router as citizen_router

app = FastAPI(
    title="FixProof Civic API",
    description="Multilingual civic complaint, infrastructure issue triage, work tracking, and repair verification platform.",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS setup supporting all development ports and production Vercel domains
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://localhost:3004",
    "http://localhost:3005",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
    "http://127.0.0.1:3003",
    "http://127.0.0.1:3004",
    "http://127.0.0.1:3005",
    "https://grama-seva-rho.vercel.app",
    "https://grama-seva.vercel.app",
]

app_base = os.getenv("APP_BASE_URL", "").rstrip("/")
if app_base and app_base not in origins:
    origins.append(app_base)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app|http://(localhost|127\.0\.0\.1):\d+",
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
app.include_router(translations_router, prefix="/api/v1")
app.include_router(assets_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(citizen_router, prefix="/api/v1")


@app.on_event("startup")
def on_startup():
    from app.core.database import Base, engine
    import app.models  # noqa: F401
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print("[Startup] Schema verification notice:", e)


@app.get("/")
def root():
    return {
        "name": "FixProof Civic API",
        "version": "0.1.0",
        "documentation": "/api/docs",
        "health": "/api/v1/health",
    }


@app.get("/health", status_code=status.HTTP_200_OK)
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
        "pilot_name": "GramaSeva Karnataka Gram Panchayat Civic Resolution",
        "supported_locales": ["en", "kn", "hi"],
        "pilot_jurisdiction": {
            "state": "Karnataka",
            "district": "Belagavi District",
            "taluk": "Belagavi Taluk",
            "default_gp": "Peeranwadi Gram Panchayat",
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
