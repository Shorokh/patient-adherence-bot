# Файл: utils/helpers.py

from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo


def parse_time_list(text: str):
    """
    Принимает строку вида "08:00,20:00" и возвращает список строк ["08:00", "20:00"].
    """
    parts = [p.strip() for p in text.split(",") if p.strip()]
    valid = []
    for p in parts:
        try:
            datetime.strptime(p, "%H:%M")
            valid.append(p)
        except ValueError:
            pass
    return valid


def calculate_next_due(time_list):
    """
    Устаревшая функция, рассчитывает ближайшее время (на сервере без учёта TZ).
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    candidates = []

    for t_str in time_list:
        dt_str = f"{today_str} {t_str}"
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        if dt > now:
            candidates.append(dt)

    if candidates:
        return min(candidates)
    else:
        # Следующее — завтра в первое время
        first = time_list[0]
        tomorrow = now + timedelta(days=1)
        dt_str = tomorrow.strftime("%Y-%m-%d") + " " + first
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")


def calculate_next_due_for_timezone(time_list, tz_str):
    """
    Рассчитывает следующий datetime (UTC-naive) для заданного списка локальных "HH:MM" 
    и часового пояса пользователя tz_str (например, "+03:00" или "Europe/Moscow").
    Возвращает naive datetime в UTC (без tzinfo), пригодный для хранения в SQLite.
    """
    # Получаем текущее UTC-время
    now_utc = datetime.now(timezone.utc)

    # Пытаемся получить объект ZoneInfo из строкового представления
    try:
        user_tz = ZoneInfo(tz_str)
    except Exception:
        # Если не удалось (например, "+03:00"), пробуем создать FixedOffset
        sign = 1 if tz_str.startswith("+") else -1
        hours = int(tz_str[1:3])
        minutes = int(tz_str[4:6]) if len(tz_str) > 3 else 0
        offset = timedelta(hours=hours, minutes=minutes) * sign
        user_tz = timezone(offset)

    # Переводим текущее время в локальное время пользователя
    now_local = now_utc.astimezone(user_tz)
    local_date = now_local.date()

    candidates = []
    for t_str in time_list:
        # Собираем локальный datetime на сегодня
        hh, mm = map(int, t_str.split(":"))
        candidate_local = datetime.combine(local_date, time(hh, mm), tzinfo=user_tz)
        if candidate_local > now_local:
            candidates.append(candidate_local)

    if not candidates:
        # Берём первое время завтра
        tomorrow = local_date + timedelta(days=1)
        hh, mm = map(int, time_list[0].split(":"))
        candidate_local = datetime.combine(tomorrow, time(hh, mm), tzinfo=user_tz)
        candidates.append(candidate_local)

    # Берём ближайший локальный вариант и переводим в UTC-naive
    next_local = min(candidates)
    next_utc = next_local.astimezone(timezone.utc)
    # Храним в БД UTC-naive
    return next_utc.replace(tzinfo=None)
