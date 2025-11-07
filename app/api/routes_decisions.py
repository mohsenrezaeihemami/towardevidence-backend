from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from pydantic import BaseModel

from app.core.database import SessionLocal
from app.models.decision import Decision, DecisionStage, DecisionOutcome
from app.models.record import Record
from app.models.audit import AuditEvent, ActorType
from app.models.file import File

router = APIRouter(prefix="/decisions", tags=["Decisions"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class DecisionOverrideRequest(BaseModel):
    record_id: str
    stage: str = "title_abstract"
    decision: DecisionOutcome
    reasons: List[str]
    created_by: str

class DecisionOverrideResponse(BaseModel):
    decision_id: str
    record_id: str
    stage: str
    decision: str
    reasons: List[str]

@router.post("/override", response_model=DecisionOverrideResponse)
def override_decision(payload: DecisionOverrideRequest, db: Session = Depends(get_db)):
    rec = db.get(Record, payload.record_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")

    stage_enum = DecisionStage(payload.stage)

    dec = Decision(
        record_id=rec.id,
        stage=stage_enum,
        decision=payload.decision,
        reasons=payload.reasons,
        qc_flag=False,
        created_by=payload.created_by,
        created_at=datetime.utcnow(),
        model_name="human_reviewer",
        prompt_version="manual",
    )
    db.add(dec)
    db.commit()
    db.refresh(dec)

    file_row = db.get(File, rec.file_id)
    project_id = file_row.project_id if file_row else None

    audit = AuditEvent(
        decision_id=dec.id,
        record_id=rec.id,
        project_id=project_id,
        actor_type=ActorType.HUMAN,
        actor_id=payload.created_by,
        action="HUMAN_OVERRIDE",
        model_name="human_reviewer",
        prompt_version="manual",
        request_payload={
            "stage": payload.stage,
            "new_decision": payload.decision.value,
            "reasons": payload.reasons,
        },
        response_payload={"decision_id": dec.id},
    )
    db.add(audit)
    db.commit()

    return DecisionOverrideResponse(
        decision_id=dec.id,
        record_id=rec.id,
        stage=stage_enum.value,
        decision=dec.decision.value,
        reasons=dec.reasons or [],
    )
