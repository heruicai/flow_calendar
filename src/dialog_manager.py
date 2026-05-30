"""Confirmation dialog state helpers for voice-driven task changes."""

from __future__ import annotations

from copy import deepcopy

from src.task_store import add_task, delete_task, mark_task_completed


CONFIRMATION_REQUIRED_INTENTS = {"add_event", "delete_event", "mark_completed"}
CONFIRM_WORDS = ("确认", "可以", "是的", "好的", "好", "确定", "执行")
CANCEL_WORDS = ("取消", "不要", "不用", "算了", "停止", "否")


def create_pending_action(parsed_command: dict, matched_task: dict | None = None) -> dict:
    """Create a serializable action that can be applied after confirmation."""
    return {
        "intent": parsed_command.get("intent"),
        "parsed_command": deepcopy(parsed_command),
        "matched_task": deepcopy(matched_task),
        "requires_confirmation": requires_confirmation(parsed_command),
    }


def requires_confirmation(parsed_command: dict) -> bool:
    """Return whether a parsed command changes stored task data."""
    return parsed_command.get("intent") in CONFIRMATION_REQUIRED_INTENTS


def build_confirmation_prompt(pending_action: dict) -> str:
    """Build a short prompt suitable for both display and speech."""
    intent = pending_action.get("intent")
    parsed = pending_action.get("parsed_command") or {}
    matched_task = pending_action.get("matched_task") or {}

    if intent == "add_event":
        task = parsed.get("task") or {}
        title = task.get("title") or "未命名任务"
        time_description = _format_task_time(task)
        return f"我理解你要添加{title}{time_description}。请点击确认添加或取消本次操作。"
    if intent == "delete_event":
        title = matched_task.get("title") or "未命名任务"
        return f"我找到任务：{title}。是否确认删除？请点击确认删除或取消本次操作。"
    if intent == "mark_completed":
        title = matched_task.get("title") or "未命名任务"
        return f"我找到任务：{title}。是否标记为完成？请点击确认完成或取消本次操作。"
    return ""


def parse_confirmation_text(text: str) -> str:
    """Interpret a short spoken or typed confirmation answer."""
    normalized = str(text or "").strip().replace(" ", "")
    if any(word in normalized for word in CANCEL_WORDS):
        return "cancel"
    if any(word in normalized for word in CONFIRM_WORDS):
        return "confirm"
    return "unknown"


def apply_confirmed_action(pending_action: dict, task_store_path=None) -> dict:
    """Apply one confirmed mutation and return a UI-friendly result."""
    intent = pending_action.get("intent")
    parsed = pending_action.get("parsed_command") or {}
    matched_task = pending_action.get("matched_task") or {}

    if intent == "add_event":
        stored_task = add_task(parsed.get("task") or {}, task_store_path)
        return _result(True, f"已添加{stored_task['title']}。", stored_task)

    task_id = matched_task.get("id")
    title = matched_task.get("title") or "任务"
    if not task_id:
        return _result(False, "没有找到可执行的任务。")

    if intent == "delete_event":
        if delete_task(task_id, task_store_path):
            return _result(True, f"已删除{title}。", matched_task)
        return _result(False, f"没有找到任务：{title}。")

    if intent == "mark_completed":
        updated_task = mark_task_completed(task_id, task_store_path)
        if updated_task:
            return _result(True, f"已将{title}标记为完成。", updated_task)
        return _result(False, f"没有找到任务：{title}。")

    return _result(False, "当前操作不支持确认执行。")


def cancel_pending_action() -> dict:
    """Return a standard cancellation result without modifying storage."""
    return _result(True, "已取消本次操作。")


def _format_task_time(task: dict) -> str:
    task_date = task.get("date")
    start_time = task.get("start_time")
    end_time = task.get("end_time")
    if task_date and start_time and end_time:
        return f"，日期是{task_date}，时间是{start_time}到{end_time}"
    if task_date and start_time:
        return f"，日期是{task_date}，时间是{start_time}"
    if task_date:
        return f"，日期是{task_date}"
    return ""


def _result(success: bool, response_text: str, task: dict | None = None) -> dict:
    return {
        "success": success,
        "response_text": response_text,
        "task": task,
    }
