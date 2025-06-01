from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from . import Base

class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medication_id = Column(Integer, ForeignKey("medications.id"))
    next_due = Column(DateTime, default=func.now())
    retry_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    medication = relationship("Medication", back_populates="reminders")
