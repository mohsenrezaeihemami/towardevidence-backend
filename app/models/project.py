import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, JSON
from app.core.database import Base


class ProtocolStatus(str, enum.Enum):
    not_uploaded = "not_uploaded"
    extracted = "extracted"
    approved = "approved"


class Project(Base):
    __tablename__ = "projects"

    # 👉 شناسه‌ی یکتا با UUID که به صورت خودکار مقدار می‌گیرد
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    protocol_config = Column(JSON, nullable=True)
    protocol_status = Column(Enum(ProtocolStatus), default=ProtocolStatus.not_uploaded)
