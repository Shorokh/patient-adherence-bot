from sqlalchemy import Column, Integer, DateTime, String, ForeignKey
from sqlalchemy.sql import func
from . import Base

class IntakeLog(Base):
    __tablename__ = "intake_logs"

    id = Column(Integer, primary_key=True, index=True)
    medication_id = Column(Integer, ForeignKey("medications.id"))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, nullable=False)
    pack_info = Column(String, nullable=True)
