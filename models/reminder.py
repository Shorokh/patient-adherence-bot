from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from . import Base

class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    medication_id = Column(Integer, ForeignKey("medications.id"))
    next_due = Column(DateTime, nullable=False)
    retry_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    double_next = Column(Boolean, default=False)

    medication = relationship("Medication", back_populates="reminders")
