import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey
from app.core.database import Base

class FileType(str, enum.Enum):
    ris = "ris"
    protocol = "protocol"
    fulltext_pdf = "fulltext_pdf"

class File(Base):
    __tablename__ = "files"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(Enum(FileType), nullable=False)
    path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
