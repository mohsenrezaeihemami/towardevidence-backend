from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.config import settings
from app.models.project import Project
from app.services.screening_ta import run_title_abstract_screening_for_project

router = APIRouter(prefix="/screening", tags=["Screening"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/title_abstract")
def run_title_abstract_screening(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.protocol_config:
        raise HTTPException(
            status_code=400,
            detail="Protocol configuration is missing. Upload protocol first.",
        )

    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured on the server.",
        )

    try:
        summary = run_title_abstract_screening_for_project(db, project_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screening failed: {e}")

    return {
        "message": "Title/abstract screening completed.",
        **summary,
    }
