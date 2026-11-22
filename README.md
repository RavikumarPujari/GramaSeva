# GramaSeva (ಗ್ರಾಮಸೇವ) — Decentralized Rural Grievance Redressal & Civic Governance Platform

GramaSeva is an end-to-end civic complaint reporting, AI-assisted triage, and grievance redressal platform engineered for rural and semi-urban Gram Panchayats. Built with Next.js, FastAPI, PostgreSQL, Google Maps, Roboflow CV models, and Google Gemini AI, it bridges rural citizens, Panchayat Development Officers (PDOs), field maintenance workers, and administrative leadership through real-time accountability and transparent tracking.

---

## 🌟 Key Features

1. **6-Stage Citizen Grievance Workflow**
   - **Geo-fencing & Reverse Geocoding:** Auto-detects exact village, taluk, district, and pin code using Google Maps Geocoding API with fallback heuristics.
   - **AI-Powered Image Analysis:** Automated severity scoring, category detection, and defect localization via Roboflow Computer Vision models.
   - **Bilingual Gemini AI Descriptions:** Automated, detailed civic grievance descriptions generated in English and Kannada.
   - **Deterministic Tracking IDs:** Unique, tamper-evident IDs (e.g., `GS-2026-BEL-10001`) with copyable tracking links and real-time status timelines.

2. **Role-Based Portals**
   - **Citizen Portal:** Report issues with photos, track grievance progress, view local village announcements, and download acknowledgment receipts.
   - **Panchayat Development Officer (PDO) Portal:** Inspect incoming grievances, review AI damage analysis, assign vetted contractors/workers with deadlines and budgets, and conduct post-repair verification.
   - **Field Worker / Contractor Portal:** Mobile-optimized interface to accept work orders, log repair progress, and upload geocoded completion evidence photos.
   - **Super Admin Portal:** Statewide/district-level analytics, department performance KPIs, SLA compliance monitors, and administrative oversight.
   - **Public Transparency Dashboard:** Real-time metrics on resolved vs. open grievances, average resolution times, category breakdown, and ward-level heatmaps.

3. **Production-Grade Resilience**
   - **PostgreSQL + Psycopg 3 Pooling:** SQLAlchemy 2.0 with connection pooling (`pool_pre_ping`, `pool_recycle`), cold-start handling, and automatic connection string normalization.
   - **Case-Insensitive Tracking:** Robust grievance lookup supporting sanitized inputs, reference numbers, and tracking UUIDs.
   - **Unified Media Pipeline:** Reliable media URL resolution across local environments and cloud deployments (Render / Vercel).

---

## 🏗️ Architecture & Technology Stack

| Layer | Technology | Description |
|---|---|---|
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS, Lucide Icons | Responsive civic interface with Kannada & English i18n |
| **Backend API** | FastAPI, Python 3.11+, Pydantic v2 | Async REST API with modular routers and OpenAPI documentation |
| **Database & ORM** | PostgreSQL 16, SQLAlchemy 2.0, Psycopg 3 | Robust relational schema across 29 tables |
| **Mapping & Location** | Google Maps JavaScript API, Google Geocoding API | Interactive map picker, ward boundaries, and reverse geocoding |
| **Artificial Intelligence** | Google Gemini 1.5/2.0 Flash, Roboflow Inference | Automated grievance summarization and computer vision triage |
| **Hosting & Deployment** | Vercel (Frontend), Render (Backend & PostgreSQL) | Scalable cloud deployment with CORS security |

---

## 📁 Repository Structure

```
GramaSeva/
├── apps/
│   └── web/                   # Next.js 14 Frontend
│       ├── src/
│       │   ├── app/           # App router ([locale] routing for en/kn/hi)
│       │   │   ├── [locale]/
│       │   │   │   ├── report/       # Citizen report workflow
│       │   │   │   ├── track/        # Public grievance tracking
│       │   │   │   ├── pdo/          # PDO dashboard & review
│       │   │   │   ├── worker/       # Field worker interface
│       │   │   │   ├── admin/        # Super Admin analytics
│       │   │   │   └── public/       # Transparency dashboard
│       │   │   └── api/              # Route handlers & proxies
│       │   ├── components/    # Reusable UI & GIS map components
│       │   └── lib/           # API client, media resolver & utilities
│       └── package.json
├── services/
│   └── api/                   # FastAPI Backend
│       ├── app/
│       │   ├── core/          # Database engine, config, security
│       │   ├── models/        # SQLAlchemy ORM models (29 tables)
│       │   ├── schemas/       # Pydantic request/response schemas
│       │   ├── public/        # Public tracking and transparency endpoints
│       │   ├── reports/       # Grievance submission and media endpoints
│       │   ├── pdo/           # PDO assignment and verification endpoints
│       │   ├── worker/        # Field worker progress and completion endpoints
│       │   └── admin/         # Super Admin oversight and analytics
│       ├── requirements.txt
│       └── render.yaml        # Render Blueprint definition
└── README.md
```

---

## 🚀 Local Development Setup

### 1. Prerequisites
- Node.js 18+ & npm / pnpm
- Python 3.11+
- PostgreSQL 15+ (or SQLite fallback for quick testing)
- Google Maps API Key

### 2. Backend Setup
```bash
# Navigate to API service
cd services/api

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables (.env)
cp .env.example .env

# Run FastAPI backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be available at `http://localhost:8000` with Swagger docs at `http://localhost:8000/docs`.

### 3. Frontend Setup
```bash
# Navigate to Next.js app
cd apps/web

# Install dependencies
npm install

# Configure environment variables (.env.local)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_google_maps_key_here

# Run development server
npm run dev
```

Frontend will be available at `http://localhost:3000`.

---

## ☁️ Production Deployment Guide

### A. Backend on Render (Web Service + Managed PostgreSQL)
1. **Managed Database:** Create a PostgreSQL instance on Render. Note the Internal Database URL.
2. **Web Service Configuration:**
   - **Root Directory:** `services/api`
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. **Environment Variables:**
   ```ini
   APP_ENV=production
   APP_BASE_URL=https://<your-render-service>.onrender.com
   DATABASE_URL=postgresql+psycopg://<username>:<password>@<internal-host>/<db_name>
   CORS_ORIGINS=https://<your-vercel-app>.vercel.app,http://localhost:3000
   GOOGLE_MAPS_API_KEY=<your_google_maps_api_key>
   GEMINI_API_KEY=<your_gemini_api_key>
   ROBOFLOW_API_KEY=<your_roboflow_api_key>
   ```

### B. Frontend on Vercel (Next.js)
1. **Framework Preset:** Next.js
2. **Root Directory:** `apps/web`
3. **Build Command:** `next build`
4. **Environment Variables:**
   ```ini
   NEXT_PUBLIC_API_URL=https://<your-render-service>.onrender.com
   NEXT_PUBLIC_API_BASE_URL=https://<your-render-service>.onrender.com
   API_BASE_URL=https://<your-render-service>.onrender.com
   NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=<your_google_maps_api_key>
   ```

---

## 🧪 Testing & Verification

- **API Health Check:** `GET /health`
- **Grievance Tracking Verification:** `GET /api/v1/public/issues/track/{tracking_id}`
- **Type Checking:** `npm --prefix apps/web run typecheck`
- **Production Build:** `npm --prefix apps/web run build`

---

## 📄 License
This project is licensed under the Apache 2.0 License.
