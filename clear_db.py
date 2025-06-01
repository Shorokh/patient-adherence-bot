from utils.db import SessionLocal
from models.intake_log import IntakeLog
from models.reminder import Reminder
from models.medication import Medication
from models.user import User

def clear_all_tables():
    session = SessionLocal()
    # Сначала удаляем “дочерние” записи, чтобы не нарушить FK
    session.query(IntakeLog).delete()
    session.query(Reminder).delete()
    session.query(Medication).delete()
    session.query(User).delete()
    session.commit()
    session.close()
    print("Все таблицы очищены.")

if __name__ == "__main__":
    clear_all_tables()
