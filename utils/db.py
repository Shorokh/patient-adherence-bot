from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base
from config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
