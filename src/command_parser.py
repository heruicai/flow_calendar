"""Rule-based parser for FlowCal voice/text commands."""

from __future__ import annotations

import re
from datetime import datetime, time, timedelta
from typing import Any


SUPPORTED_INTENTS = {
    "add_event",
    "delete_event",
    "query_schedule",
    "mark_completed",
}

SUPPORTED_TASK_TYPES = {
    "fixed_event",
    "deadline_task",
    "essential_task",
    "flexible_plan",
}

DISPLAY_MODES_BY_TYPE = {
    "fixed_event": "calendar_block",
    "deadline_task": "deadline_bar",
    "essential_task": "essential_bar",
    "flexible_plan": "todo_pool",
}

FIXED_EVENT_KEYWORDS = ("面试", "会议", "笔试", "上课", "答辩", "组会")
DEADLINE_KEYWORDS = ("截止", "deadline", "ddl", "DDL")
ESSENTIAL_KEYWORDS = ("洗衣服", "吃饭", "洗澡", "买药", "取快递", "交水电费")
ESSENTIAL_HINTS = ("必须", "记得", "别忘了")
FLEXIBLE_KEYWORDS = ("弹性任务", "刷题", "复习", "阅读", "整理资料", "LeetCode", "leetcode")

WEEKDAYS = {
    "一": 0,
    "二": 1,
    "三": 2,
    "四": 3,
    "五": 4,
    "六": 5,
    "日": 6,
    "天": 6,
}

CHINESE_NUMBERS = {
    "零": 0,
    "一": 1,
    "两": 2,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "十一": 11,
    "十二": 12,
}


def parse_command(text: str, now: datetime | None = None) -> dict:
    """Parse one FlowCal command from typed text or simulated ASR output."""
    current_time = now or datetime.now()
    command = text.strip()
    intent = _detect_intent(command)
    date_info = _parse_date(command, current_time)
    duration_minutes = _parse_duration_minutes(command)
    start_time, end_time = _parse_time_range(command)
    deadline = _parse_deadline(command, current_time)
    task_type = _detect_task_type(command, start_time, deadline)
    title = _extract_title(command, intent)

    result = {
        "intent": intent,
        "need_clarification": False,
        "clarification_question": "",
        "task": None,
        "query": {
            "date": date_info["date"],
            "keyword": title if intent in {"delete_event", "mark_completed"} else "",
        },
        "response_text": "",
    }

    if intent == "query_schedule":
        if not date_info["date"]:
            return _with_clarification(result, "请补充要查看哪一天的日程")
        result["response_text"] = f"正在查看 {date_info['date']} 的日程。"
        return result

    if intent in {"delete_event", "mark_completed"}:
        if not title:
            return _with_clarification(result, "请补充任务名称")
        result["response_text"] = _build_action_response(intent, title)
        return result

    task = {
        "title": title,
        "type": task_type,
        "date": date_info["date"],
        "start_time": start_time,
        "end_time": end_time,
        "deadline": _format_datetime(deadline),
        "estimated_duration_minutes": duration_minutes,
        "latest_start_time": _format_datetime(
            deadline - timedelta(minutes=duration_minutes)
            if deadline and duration_minutes
            else None
        ),
        "preferred_time_window": date_info["preferred_time_window"],
        "status": "pending",
        "display_mode": DISPLAY_MODES_BY_TYPE[task_type],
        "notes": "",
    }
    result["task"] = task

    clarification_question = _validate_add_task(command, task)
    if clarification_question:
        return _with_clarification(result, clarification_question)

    result["response_text"] = f"已解析为 {task_type}：{title}"
    return result


def _detect_intent(text: str) -> str:
    if any(keyword in text for keyword in ("删除", "删掉", "取消")):
        return "delete_event"
    if any(keyword in text for keyword in ("什么安排", "查看", "日程", "安排")):
        return "query_schedule"
    if any(keyword in text for keyword in ("已完成", "完成了", "标记为完成", "标记完成")):
        return "mark_completed"
    return "add_event"


def _detect_task_type(text: str, start_time: str | None, deadline: datetime | None) -> str:
    if "弹性任务" in text:
        return "flexible_plan"
    if deadline or any(keyword in text for keyword in DEADLINE_KEYWORDS):
        return "deadline_task"
    if any(keyword in text for keyword in ESSENTIAL_KEYWORDS + ESSENTIAL_HINTS):
        return "essential_task"
    if start_time and any(keyword in text for keyword in FIXED_EVENT_KEYWORDS):
        return "fixed_event"
    if any(keyword in text for keyword in FLEXIBLE_KEYWORDS):
        return "flexible_plan"
    if start_time:
        return "fixed_event"
    return "flexible_plan"


def _parse_date(text: str, now: datetime) -> dict[str, str | None]:
    preferred_time_window = _parse_preferred_time_window(text)

    if "后天" in text:
        target_date = now.date() + timedelta(days=2)
    elif "明天" in text or "明晚" in text:
        target_date = now.date() + timedelta(days=1)
    elif "今天" in text or "今晚" in text:
        target_date = now.date()
    else:
        target_date = _parse_weekday_date(text, now)

    return {
        "date": target_date.isoformat() if target_date else None,
        "preferred_time_window": preferred_time_window,
    }


def _parse_weekday_date(text: str, now: datetime):
    match = re.search(r"(下周)?周([一二三四五六日天])", text)
    if not match:
        return None

    target_weekday = WEEKDAYS[match.group(2)]
    days_ahead = (target_weekday - now.weekday()) % 7
    if match.group(1):
        days_ahead += 7
    elif days_ahead == 0:
        days_ahead = 7

    return now.date() + timedelta(days=days_ahead)


def _parse_preferred_time_window(text: str) -> str | None:
    if "上午" in text:
        return "morning"
    if "下午" in text:
        return "afternoon"
    if "晚上" in text or "今晚" in text or "明晚" in text:
        return "evening"
    return None


def _parse_deadline(text: str, now: datetime) -> datetime | None:
    if not _has_deadline_expression(text):
        return None

    date_info = _parse_date(text, now)
    deadline_date = datetime.fromisoformat(date_info["date"]).date() if date_info["date"] else now.date()
    parsed_time, _ = _parse_time_range(text)

    if parsed_time:
        hour, minute = _split_time(parsed_time)
        return datetime.combine(deadline_date, time(hour, minute))

    if date_info["preferred_time_window"] == "evening":
        return datetime.combine(deadline_date, time(23, 0))

    return datetime.combine(deadline_date, time(23, 59))


def _has_deadline_expression(text: str) -> bool:
    return (
        any(keyword in text for keyword in DEADLINE_KEYWORDS)
        or bool(re.search(r"(今天|明天|后天|今晚|明晚|周[一二三四五六日天]|下周[一二三四五六日天]).{0,4}(前|之前)", text))
    )


def _parse_time_range(text: str) -> tuple[str | None, str | None]:
    time_tokens = list(_iter_time_tokens(text))
    if not time_tokens:
        return None, None

    first_token = time_tokens[0]
    start_time = _format_time(first_token["hour"], first_token["minute"])
    end_time = None

    if len(time_tokens) >= 2 and _is_range_text(text, first_token["end"], time_tokens[1]["start"]):
        second_token = time_tokens[1]
        end_hour = second_token["hour"]
        if second_token["period"] is None and first_token["period"] in {"下午", "晚上"} and end_hour < 12:
            end_hour += 12
        end_time = _format_time(end_hour, second_token["minute"])

    return start_time, end_time


def _iter_time_tokens(text: str):
    pattern = re.compile(r"(上午|下午|晚上|今晚|明晚)?\s*(\d{1,2}[:：]\d{1,2}|[零一二两三四五六七八九十]{1,3}|\d{1,2})\s*(点|时)?")
    for match in pattern.finditer(text):
        raw_number = match.group(2)
        has_time_marker = bool(match.group(3) or ":" in raw_number or "：" in raw_number)
        if not has_time_marker:
            continue

        hour, minute = _parse_time_number(raw_number)
        period = match.group(1)
        hour = _apply_period(hour, period)
        yield {
            "hour": hour,
            "minute": minute,
            "period": period,
            "start": match.start(),
            "end": match.end(),
        }


def _parse_time_number(raw_number: str) -> tuple[int, int]:
    if ":" in raw_number or "：" in raw_number:
        hour_text, minute_text = re.split(r"[:：]", raw_number, maxsplit=1)
        return int(hour_text), int(minute_text)
    return _parse_number(raw_number), 0


def _apply_period(hour: int, period: str | None) -> int:
    if period in {"下午", "晚上", "今晚", "明晚"} and 1 <= hour < 12:
        return hour + 12
    return hour


def _is_range_text(text: str, first_end: int, second_start: int) -> bool:
    between = text[first_end:second_start]
    return bool(re.search(r"(到|至|-|~|—)", between))


def _parse_duration_minutes(text: str) -> int | None:
    if "半小时" in text:
        return 30

    match = re.search(r"(预计|大概|需要)?\s*(\d+(?:\.\d+)?|[一二两三四五六七八九十]{1,3})\s*(个)?小时", text)
    if match:
        return int(float(_parse_numeric_text(match.group(2))) * 60)

    match = re.search(r"(预计|大概|需要)?\s*(\d+|[一二两三四五六七八九十]{1,3})\s*分钟", text)
    if match:
        return int(_parse_numeric_text(match.group(2)))

    return None


def _parse_numeric_text(value: str) -> float:
    try:
        return float(value)
    except ValueError:
        return float(_parse_number(value))


def _parse_number(value: str) -> int:
    if value.isdigit():
        return int(value)
    if value in CHINESE_NUMBERS:
        return CHINESE_NUMBERS[value]
    if value.startswith("十"):
        return 10 + CHINESE_NUMBERS.get(value[1:], 0)
    if "十" in value:
        tens, ones = value.split("十", maxsplit=1)
        return CHINESE_NUMBERS.get(tens, 1) * 10 + CHINESE_NUMBERS.get(ones, 0)
    return 0


def _format_time(hour: int, minute: int) -> str:
    return f"{hour:02d}:{minute:02d}"


def _split_time(value: str) -> tuple[int, int]:
    hour, minute = value.split(":", maxsplit=1)
    return int(hour), int(minute)


def _format_datetime(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%S") if value else None


def _extract_title(text: str, intent: str) -> str:
    title = text.strip()
    title = re.sub(r"[，。,.\s]+$", "", title)
    title = re.sub(r"(预计|大概|需要)?\s*(\d+(?:\.\d+)?|[一二两三四五六七八九十]{1,3}|半)\s*(个)?(小时|分钟)", "", title)
    title = re.sub(r"(今天|明天|后天|今晚|明晚|上午|下午|晚上|下周[一二三四五六日天]|周[一二三四五六日天])", "", title)
    title = re.sub(r"(\d{1,2}[:：]\d{1,2}|[零一二两三四五六七八九十]{1,3}|\d{1,2})\s*(点|时)", "", title)
    title = re.sub(r"(到|至|-|~|—)", "", title)
    title = re.sub(r"(前|之前|截止|deadline|ddl|DDL)", "", title)

    if intent == "delete_event":
        title = re.sub(r"^(删除|把)?", "", title)
        title = re.sub(r"(删掉|删除|取消)$", "", title)
    elif intent == "mark_completed":
        title = re.sub(r"^(把)?", "", title)
        title = re.sub(r"(标记为完成|标记完成|已完成|完成了)$", "", title)
    else:
        title = re.sub(r"^(添加|新增|创建)?(一个)?(弹性任务|任务|日程)?[,，]?", "", title)
        title = re.sub(r"^(参加|完成|提醒我|记得|别忘了|必须)", "", title)

    return title.strip(" ，,。的")


def _validate_add_task(text: str, task: dict[str, Any]) -> str:
    if not task["title"]:
        return "请补充任务名称"
    if task["type"] == "fixed_event" and not task["date"]:
        return "请补充具体日期"
    if task["type"] == "fixed_event" and not task["start_time"]:
        return "请补充具体时间"
    if task["type"] == "deadline_task" and not task["deadline"]:
        return "请补充截止日期"
    if _looks_like_reminder_without_time(text, task):
        return "请补充具体时间"
    return ""


def _looks_like_reminder_without_time(text: str, task: dict[str, Any]) -> bool:
    return (
        "提醒我" in text
        and task["type"] == "flexible_plan"
        and task["date"]
        and not task["start_time"]
        and not task["deadline"]
    )


def _with_clarification(result: dict, question: str) -> dict:
    result["need_clarification"] = True
    result["clarification_question"] = question
    result["response_text"] = question
    return result


def _build_action_response(intent: str, title: str) -> str:
    if intent == "delete_event":
        return f"准备删除：{title}"
    if intent == "mark_completed":
        return f"准备标记完成：{title}"
    return ""
