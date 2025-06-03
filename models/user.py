from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from . import Base

class User(Base):
    __tablename__ = "users"

    telegram_id = Column(Integer, primary_key=True, index=True)
    language = Column(String, default="ru")
    ui_mode = Column(String, default="standard")
    role = Column(String, default="patient")
    timezone = Column(String, nullable=True)
    assistant_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=True)

    medications = relationship("Medication", back_populates="owner")
