from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.database import SessionLocal
from app.models.record import Record
from app.models.file import File
from app.models.decision import Decision, DecisionStage

router = APIRouter(prefix="/records", tags=["Records"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class RecordWithDecision(BaseModel):
    id: str
    title: Optional[str]
    year: Optional[int]
    decision: Optional[str]
    reasons: list[str] = []
    verbatim_quote: Optional[str] = None
    quote_location: Optional[str] = None
    qc_flag: bool = False

    class Config:
        orm_mode = True

class DecisionInfo(BaseModel):
    stage: str
    decision: Optional[str]
    reasons: list[str] = []
    verbatim_quote: Optional[str] = None
    quote_location: Optional[str] = None
    qc_flag: bool = False
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    decided_at: Optional[datetime] = None

class RecordDetail(BaseModel):
    id: str
    project_id: str
    title: Optional[str]
    authors: Optional[str]
    journal: Optional[str]
    year: Optional[int]
    language: Optional[str]
    sample_size: Optional[int]
    abstract: Optional[str]
    decision_ta: Optional[DecisionInfo] = None

    class Config:
        orm_mode = True

@router.get("/", response_model=List[RecordWithDecision])
def list_records(
    project_id: str = Query(...),
    stage: str = Query("title_abstract"),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        """
        SELECT r.id, r.title, r.year
        FROM records r
        JOIN files f ON r.file_id = f.id
        WHERE f.project_id = :pid
        ORDER BY r.order_index
        """,
        {"pid": project_id},
    ).fetchall()

    results: list[RecordWithDecision] = []
    for row in rows:
        rec_id = row.id
        dec = (
            db.query(Decision)
            .filter(
                Decision.record_id == rec_id,
                Decision.stage == DecisionStage(stage),
            )
            .order_by(Decision.created_at.desc())
            .first()
        )
        if dec:
            results.append(
                RecordWithDecision(
                    id=rec_id,
                    title=row.title,
                    year=row.year,
                    decision=dec.decision.value if dec.decision else None,
                    reasons=dec.reasons or [],
                    verbatim_quote=dec.verbatim_quote,
                    quote_location=dec.quote_location,
                    qc_flag=dec.qc_flag,
                )
            )
        else:
            results.append(
                RecordWithDecision(
                    id=rec_id,
                    title=row.title,
                    year=row.year,
                    decision=None,
                    reasons=[],
                    verbatim_quote=None,
                    quote_location=None,
                    qc_flag=False,
                )
            )
    return results

@router.get("/{record_id}", response_model=RecordDetail)
def get_record_detail(record_id: str, db: Session = Depends(get_db)):
    rec = db.get(Record, record_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")

    file_row = db.get(File, rec.file_id)
    if not file_row:
        raise HTTPException(status_code=500, detail="File missing for record")

    dec_ta = (
        db.query(Decision)
        .filter(
            Decision.record_id == rec.id,
            Decision.stage == DecisionStage.title_abstract,
        )
        .order_by(Decision.created_at.desc())
        .first()
    )

    dec_info = None
    if dec_ta:
        dec_info = DecisionInfo(
            stage=dec_ta.stage.value,
            decision=dec_ta.decision.value if dec_ta.decision else None,
            reasons=dec_ta.reasons or [],
            verbatim_quote=dec_ta.verbatim_quote,
            quote_location=dec_ta.quote_location,
            qc_flag=dec_ta.qc_flag,
            model_name=dec_ta.model_name,
            prompt_version=dec_ta.prompt_version,
            decided_at=dec_ta.created_at,
        )

    return RecordDetail(
        id=rec.id,
        project_id=file_row.project_id,
        title=rec.title,
        authors=rec.authors,
        journal=rec.journal,
        year=rec.year,
        language=rec.language,
        sample_size=rec.sample_size,
        abstract=rec.abstract,
        decision_ta=dec_info,
    )
