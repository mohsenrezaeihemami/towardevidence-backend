import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, JSON, Boolean, Text, ForeignKey
from app.core.database import Base

class DecisionStage(str, enum.Enum):
    title_abstract = "title_abstract"
    full_text = "full_text"

class DecisionOutcome(str, enum.Enum):
    include = "include"
    exclude = "exclude"
    unclear = "unclear"

class Decision(Base):
    __tablename__ = "decisions"

    id = Column(String, primary_key=True)
    record_id = Column(String, ForeignKey("records.id", ondelete="CASCADE"), nullable=False)

    stage = Column(Enum(DecisionStage), nullable=False)
    decision = Column(Enum(DecisionOutcome), nullable=False)
    reasons = Column(JSON, nullable=True)

    verbatim_quote = Column(Text, nullable=True)
    quote_location = Column(String, nullable=True)

    qc_flag = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, nullable=False)
    model_name = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)
