# ============================================
# File: app/main.py
# TowardEvidence Backend — FastAPI entrypoint
# ============================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.api import (
    routes_project,
    routes_files,
    routes_records,
    routes_decisions,
    routes_audit,
    routes_screening,
    routes_export,
)

# ---------------------------------------------------
# 1. Database Initialization
# ---------------------------------------------------
# اگر دیتابیس SQLite باشد، در اولین اجرا فایل slr.db ساخته می‌شود.
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------
# 2. FastAPI Application
# ---------------------------------------------------
app = FastAPI(
    title="TowardEvidence Backend",
    version="0.1.0",
    description="Backend API for systematic review management and AI-assisted screening.",
)

# ---------------------------------------------------
# 3. CORS Middleware (Allow Frontend Access)
# ---------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # در محیط تولیدی بهتر است دامنه مشخص شود
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------
# 4. Include Routers
# ---------------------------------------------------
app.include_router(routes_project.router)
app.include_router(routes_files.router)
app.include_router(routes_records.router)
app.include_router(routes_decisions.router)
app.include_router(routes_audit.router)
app.include_router(routes_screening.router)
app.include_router(routes_export.router)

# ---------------------------------------------------
# 5. Root Endpoint (Health Check)
# ---------------------------------------------------
@app.get("/")
def read_root():
    """
    Root endpoint — use to check if the backend is running.
    """
    return {"message": "TowardEvidence backend is running"}

# ---------------------------------------------------
# 6. Main Entrypoint (optional for local debug)
# ---------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
