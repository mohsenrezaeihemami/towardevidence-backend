from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey
from app.core.database import Base

class Record(Base):
    __tablename__ = "records"

    id = Column(String, primary_key=True)
    file_id = Column(String, ForeignKey("files.id", ondelete="CASCADE"), nullable=False)

    order_index = Column(Integer, nullable=True)

    title = Column(Text, nullable=True)
    abstract = Column(Text, nullable=True)
    year = Column(Integer, nullable=True)
    language = Column(String, nullable=True)
    sample_size = Column(Integer, nullable=True)

    doi = Column(String, nullable=True)
    journal = Column(String, nullable=True)
    authors = Column(Text, nullable=True)

    metadata_quality = Column(Float, nullable=True)
