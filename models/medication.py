from sqlalchemy import Column, Integer, String, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from . import Base

class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"))
    name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    intake_type = Column(String, nullable=False)
    time_list = Column(JSON, default=[])
    conditions = Column(JSON, default=[])
    skip_behavior = Column(String, default="")
    is_active = Column(Boolean, default=True)

    owner = relationship("User", back_populates="medications")
    reminders = relationship("Reminder", back_populates="medication", cascade="all, delete-orphan")
