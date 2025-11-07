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

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TowardEvidence Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_project.router)
app.include_router(routes_files.router)
app.include_router(routes_records.router)
app.include_router(routes_decisions.router)
app.include_router(routes_audit.router)
app.include_router(routes_screening.router)
app.include_router(routes_export.router)

@app.get("/")
def read_root():
    return {"message": "TowardEvidence backend is running"}
