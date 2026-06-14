"""
main.py — VisualAgro FastAPI Backend
=====================================
Stack  : FastAPI · Uvicorn · SQLAlchemy · Pydantic v2 · JWT Auth
DB     : SQLite (dev, default) → PostgreSQL (prod via DATABASE_URL env var)
Auth   : JWT Bearer tokens  (HS256, 24 h expiry)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from routers  import auth, dashboard, stock, reorder, insights, alerts, ai, inventory, phase4

# ── Create all tables on startup (dev convenience; use Alembic in prod) ──
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title       = "VisualAgro API",
    description = (
        "Backend for **VisualAgro** — the AI-powered vendor dashboard.\n\n"
        "Screens served:\n"
        "- 🏠 **Dashboard** — stat cards, spoilage alerts, stock snapshot\n"
        "- 📋 **Stock Entry** — end-of-day log submission\n"
        "- 🛒 **Reorder / Buy List** — AI suggestions + WhatsApp share\n"
        "- 📊 **Insights** — weekly KPIs, charts, best-sellers\n\n"
        "All endpoints (except `/auth/*`) require a Bearer JWT."
    ),
    version     = "1.0.0",
    contact     = {"name": "VisualAgro", "email": "dev@visualagro.in"},
    license_info= {"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Routers ──────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(stock.router)
app.include_router(reorder.router)
app.include_router(insights.router)
app.include_router(alerts.router)
app.include_router(ai.router)
app.include_router(inventory.router)
app.include_router(phase4.router)

# Optional direct alias for dashboard-style alert URLs
app.include_router(alerts.router, prefix="/dashboard")


@app.get("/", tags=["Health"], summary="Health check")
def root():
    return {
        "service": "VisualAgro API",
        "status" : "ok",
        "version": "1.0.0",
        "docs"   : "/docs",
    }
