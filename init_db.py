from utils.db import Base, engine

# Импортируем все модели, чтобы заполнить Base.metadata
import models.user
import models.medication
import models.reminder
import models.intake_log

def init():
    Base.metadata.create_all(bind=engine)
    print("База данных создана/обновлена.")

if __name__ == "__main__":
    init()
