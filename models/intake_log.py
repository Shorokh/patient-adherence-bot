from sqlalchemy import Column, Integer, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from . import Base

class IntakeLog(Base):
    __tablename__ = "intake_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medication_id = Column(Integer, ForeignKey("medications.id"))
    timestamp = Column(DateTime, default=func.now())
    status = Column(String)          # "taken" или "skipped"
    pack_info = Column(String, nullable=True)

    medication = relationship("Medication", back_populates="intake_logs")
