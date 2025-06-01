from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from . import Base

class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"))
    name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    intake_type = Column(String, default="regular")   # "regular" или "situational"
    time_list = Column(JSON, default=[])              # список строк "HH:MM"
    conditions = Column(JSON, default=[])             # ["до еды", "с водой", ...]
    skip_behavior = Column(String, default="skip")    # "double", "skip", "notify" и т.п.
    is_active = Column(Boolean, default=True)

    owner = relationship("User", back_populates="medications")
    reminders = relationship("Reminder", back_populates="medication", cascade="all, delete-orphan")
    intake_logs = relationship("IntakeLog", back_populates="medication", cascade="all, delete-orphan")
