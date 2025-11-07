import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, JSON, ForeignKey
from app.core.database import Base

class ActorType(str, enum.Enum):
    SYSTEM = "SYSTEM"
    AI = "AI"
    HUMAN = "HUMAN"

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    record_id = Column(String, ForeignKey("records.id", ondelete="CASCADE"), nullable=True)
    decision_id = Column(String, ForeignKey("decisions.id", ondelete="SET NULL"), nullable=True)

    actor_type = Column(Enum(ActorType), nullable=False)
    actor_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    model_name = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)

    request_payload = Column(JSON, nullable=True)
    response_payload = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
