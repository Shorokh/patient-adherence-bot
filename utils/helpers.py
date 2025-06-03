from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo

def parse_time_list(text: str):
    parts = [p.strip() for p in text.split(",") if p.strip()]
    valid = []
    for p in parts:
        try:
            datetime.strptime(p, "%H:%M")
            valid.append(p)
        except ValueError:
            pass
    return valid

def calculate_next_due_for_timezone(time_list, tz_str):
    now_utc = datetime.now(timezone.utc)
    try:
        user_tz = ZoneInfo(tz_str)
    except Exception:
        sign = 1 if tz_str.startswith("+") else -1
        hours = int(tz_str[1:3])
        minutes = int(tz_str[4:6]) if len(tz_str) > 3 else 0
        offset = timedelta(hours=hours, minutes=minutes) * sign
        user_tz = timezone(offset)

    now_local = now_utc.astimezone(user_tz)
    local_date = now_local.date()
    candidates = []
    for t_str in time_list:
        hh, mm = map(int, t_str.split(":"))
        candidate_local = datetime.combine(local_date, time(hh, mm), tzinfo=user_tz)
        if candidate_local > now_local:
            candidates.append(candidate_local)

    if not candidates:
        tomorrow = local_date + timedelta(days=1)
        hh, mm = map(int, time_list[0].split(":"))
        candidate_local = datetime.combine(tomorrow, time(hh, mm), tzinfo=user_tz)
        candidates.append(candidate_local)

    next_local = min(candidates)
    next_utc = next_local.astimezone(timezone.utc)
    return next_utc.replace(tzinfo=None)
