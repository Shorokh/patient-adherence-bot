# Простейшая мультиязычность через словари
MESSAGES = {
    "ru": {
        "welcome": "Привет! Выберите язык:",
        "select_ui": "Выберите режим интерфейса:",
        "select_role": "Выберите роль (пациент или помощник):",
        # Добавляйте другие строки по необходимости
    },
    "en": {
        "welcome": "Hello! Please choose your language:",
        "select_ui": "Select UI mode:",
        "select_role": "Select your role (patient or assistant):",
        # Другие переводы
    }
}

def t(lang: str, key: str) -> str:
    return MESSAGES.get(lang, MESSAGES["ru"]).get(key, "")
