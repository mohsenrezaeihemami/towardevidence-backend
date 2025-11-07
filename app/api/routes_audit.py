from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel

from app.core.database import SessionLocal
from app.models.audit import AuditEvent

router = APIRouter(prefix="/audit", tags=["Audit"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class AuditEventOut(BaseModel):
    id: str
    time: datetime
    actor_type: str
    action: str
    model_name: str | None = None
    prompt_version: str | None = None
    summary: str | None = None

    class Config:
        orm_mode = True

@router.get("/record/{record_id}", response_model=List[AuditEventOut])
def get_audit_for_record(record_id: str, db: Session = Depends(get_db)):
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.record_id == record_id)
        .order_by(AuditEvent.created_at.asc())
        .all()
    )
    result: list[AuditEventOut] = []
    for ev in events:
        summary = ev.action
        if ev.response_payload and isinstance(ev.response_payload, dict):
            reasons = ev.response_payload.get("reasons")
            if isinstance(reasons, list) and reasons:
                summary += " – " + "; ".join(reasons[:2])
        result.append(
            AuditEventOut(
                id=ev.id,
                time=ev.created_at,
                actor_type=ev.actor_type.value if hasattr(ev.actor_type, "value") else ev.actor_type,
                action=ev.action,
                model_name=ev.model_name,
                prompt_version=ev.prompt_version,
                summary=summary,
            )
        )
    return result
