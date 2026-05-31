"""Local Chinese temporal candidate parsing."""

from __future__ import annotations

import re
from datetime import datetime, timedelta


CHINESE_DIGITS = {
    "\u96f6": 0, "\u4e00": 1, "\u4e8c": 2, "\u4e24": 2, "\u4e09": 3,
    "\u56db": 4, "\u4e94": 5, "\u516d": 6, "\u4e03": 7, "\u516b": 8,
    "\u4e5d": 9, "\u5341": 10,
}
WEEKDAYS = {"\u4e00": 0, "\u4e8c": 1, "\u4e09": 2, "\u56db": 3, "\u4e94": 4, "\u516d": 5, "\u65e5": 6, "\u5929": 6}


def parse_number(value: str) -> int | None:
    if value.isdigit():
        return int(value)
    if value in CHINESE_DIGITS:
        return CHINESE_DIGITS[value]
    if value.startswith("\u5341"):
        return 10 + CHINESE_DIGITS.get(value[1:], 0)
    if "\u5341" in value:
        tens, ones = value.split("\u5341", 1)
        return CHINESE_DIGITS.get(tens, 1) * 10 + CHINESE_DIGITS.get(ones, 0)
    return None


def parse_temporal_candidates(text: str, *, now: datetime | None = None) -> list[dict]:
    current = now or datetime.now()
    result: dict[str, str | None] = {"date": None, "start_time": None, "end_time": None}
    if "\u4eca\u5929" in text:
        result["date"] = current.date().isoformat()
    elif "\u660e\u5929" in text:
        result["date"] = (current.date() + timedelta(days=1)).isoformat()
    elif "\u540e\u5929" in text:
        result["date"] = (current.date() + timedelta(days=2)).isoformat()
    else:
        days = re.search(r"([0-9\u4e00\u4e8c\u4e24\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]+)\u5929\u540e", text)
        weekday = re.search(r"(\u4e0b)?(?:\u5468|\u661f\u671f)([\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u65e5\u5929])", text)
        explicit = re.search(r"(?:(\d{4})\u5e74)?(\d{1,2})\u6708(\d{1,2})[\u65e5\u53f7]", text)
        if days and parse_number(days.group(1)) is not None:
            result["date"] = (current.date() + timedelta(days=parse_number(days.group(1)) or 0)).isoformat()
        elif weekday:
            offset = (WEEKDAYS[weekday.group(2)] - current.weekday()) % 7
            if weekday.group(1):
                offset += 7 if offset == 0 else 7
            elif offset == 0:
                offset = 7
            result["date"] = (current.date() + timedelta(days=offset)).isoformat()
        elif explicit:
            result["date"] = datetime(int(explicit.group(1) or current.year), int(explicit.group(2)), int(explicit.group(3))).date().isoformat()
    tokens = list(_time_tokens(text))
    if tokens:
        result["start_time"] = tokens[0]
    if len(tokens) > 1 and re.search(r"(?:\u5230|\u81f3|-|~)", text):
        result["end_time"] = tokens[1]
    return [result] if any(result.values()) else []


def _time_tokens(text: str):
    pattern = re.compile(r"(\u4e0a\u5348|\u4e0b\u5348|\u665a\u4e0a)?([0-9]{1,2}|[\u96f6\u4e00\u4e8c\u4e24\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]{1,3})\u70b9(\u534a|\u4e00\u523b)?")
    for match in pattern.finditer(text):
        hour = parse_number(match.group(2))
        if hour is None:
            continue
        if match.group(1) in {"\u4e0b\u5348", "\u665a\u4e0a"} and hour < 12:
            hour += 12
        minute = 30 if match.group(3) == "\u534a" else 15 if match.group(3) == "\u4e00\u523b" else 0
        yield f"{hour:02d}:{minute:02d}"
