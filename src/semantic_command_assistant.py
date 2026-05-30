"""Local rule-based task matching and update planning helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from src.task_store import DISPLAY_MODES_BY_TYPE, update_task, update_task_type


def find_candidate_tasks(
    tasks: list[dict],
    target_keyword: str,
    target_date: str | None = None,
    task_type: str | None = None,
) -> list[dict]:
    """Return matching tasks, preferring title, date, and type evidence."""
    keyword = str(target_keyword or "").strip().lower()
    if not keyword:
        return []

    candidates = [
        task
        for task in tasks
        if keyword in str(task.get("title") or "").lower()
        or str(task.get("title") or "").lower() in keyword
    ]
    if target_date:
        dated = [task for task in candidates if task.get("date") == target_date]
        if dated:
            candidates = dated
    if task_type:
        typed = [task for task in candidates if task.get("type") == task_type]
        if typed:
            candidates = typed
    return candidates


def build_update_plan(parsed_command: dict, tasks: list[dict]) -> dict:
    """Match an update command to one task and prepare a validated draft."""
    target = parsed_command.get("target") or {}
    updates = dict(parsed_command.get("updates") or {})
    keyword = str(target.get("keyword") or "").strip()
    candidates = find_candidate_tasks(
        tasks,
        keyword,
        target_date=target.get("date"),
        task_type=_infer_target_type(parsed_command),
    )
    base = {
        "intent": "update_event",
        "need_clarification": False,
        "clarification_question": "",
        "matched_task": None,
        "updates": updates,
    }
    if not keyword:
        return _clarify(base, "你想修改哪个任务？")
    if not candidates:
        return _clarify(base, f"没有找到匹配任务：{keyword}。请说出更准确的任务名称。")
    if len(candidates) > 1:
        labels = "、".join(_candidate_label(task) for task in candidates)
        return _clarify(base, f"找到多个匹配任务：{labels}。请说明你想修改哪一个。")

    matched_task = candidates[0]
    validation_question = _validate_updates(matched_task, updates)
    base["matched_task"] = matched_task
    if validation_question:
        return _clarify(base, validation_question)
    return base


def build_update_confirmation(update_plan: dict) -> str:
    """Build a concise confirmation prompt for one update draft."""
    task = update_plan.get("matched_task") or {}
    updates = update_plan.get("updates") or {}
    title = task.get("title") or "未命名任务"
    details = []
    if updates.get("date"):
        details.append(f"日期改为 {updates['date']}")
    if updates.get("start_time") and updates.get("end_time"):
        details.append(f"时间改为 {updates['start_time']} 到 {updates['end_time']}")
    elif updates.get("start_time"):
        details.append(f"开始时间改为 {updates['start_time']}")
    if updates.get("deadline"):
        details.append(f"截止时间改为 {_format_datetime(updates['deadline'])}")
    if updates.get("type"):
        details.append(f"任务类型改为 {updates['type']}")
    if updates.get("estimated_duration_minutes"):
        details.append(f"预计耗时改为 {updates['estimated_duration_minutes']} 分钟")
    summary = "，".join(details) or "更新任务信息"
    return f"我找到任务：{title}。你想把{summary}，是否确认？"


def apply_update_plan(update_plan: dict, task_store_path=None) -> dict:
    """Persist one confirmed semantic update plan."""
    task = update_plan.get("matched_task") or {}
    task_id = task.get("id")
    updates = dict(update_plan.get("updates") or {})
    if not task_id:
        return _result(False, "没有找到可修改的任务。")

    try:
        effective_updates = _derive_updates(task, updates)
        if effective_updates.get("type") and effective_updates["type"] != task.get("type"):
            updated_task = update_task_type(
                task_id,
                effective_updates["type"],
                selected_date=effective_updates.get("date"),
                updates=effective_updates,
                path=task_store_path,
            )
        else:
            updated_task = update_task(task_id, effective_updates, task_store_path)
    except ValueError as exc:
        return _result(False, str(exc))

    if not updated_task:
        return _result(False, "没有找到可修改的任务。")
    return _result(True, f"已修改任务：{updated_task['title']}。", updated_task)


def _derive_updates(task: dict, updates: dict) -> dict:
    derived = dict(updates)
    target_type = derived.get("type") or task.get("type")
    if target_type:
        derived["display_mode"] = DISPLAY_MODES_BY_TYPE[target_type]

    if target_type == "deadline_task":
        deadline = derived.get("deadline") or task.get("deadline")
        duration = (
            derived["estimated_duration_minutes"]
            if "estimated_duration_minutes" in derived
            else task.get("estimated_duration_minutes")
        )
        if not deadline:
            raise ValueError("请补充新的截止时间。")
        derived["deadline"] = deadline
        derived["estimated_duration_minutes"] = duration
        derived["latest_start_time"] = _latest_start_time(deadline, duration)
    return derived


def _validate_updates(task: dict, updates: dict) -> str:
    if not updates:
        return "你想修改任务的时间、截止时间，还是任务类型？"
    target_type = updates.get("type") or task.get("type")
    merged = dict(task)
    merged.update(updates)
    if target_type == "fixed_event":
        if not all(merged.get(field) for field in ("date", "start_time", "end_time")):
            return "固定时间任务需要日期、开始时间和结束时间，请补充完整。"
    if target_type == "deadline_task" and not merged.get("deadline"):
        return "截止任务需要截止时间，请补充新的截止时间。"
    if target_type == "essential_task" and not merged.get("date"):
        return "生活必需任务需要日期，请补充任务日期。"
    return ""


def _infer_target_type(parsed_command: dict) -> str | None:
    target = parsed_command.get("target") or {}
    if target.get("type"):
        return target["type"]
    updates = parsed_command.get("updates") or {}
    if updates.get("deadline"):
        return "deadline_task"
    if updates.get("start_time"):
        return "fixed_event"
    return None


def _latest_start_time(deadline: str, duration: int | None) -> str | None:
    if not duration:
        return None
    parsed = datetime.fromisoformat(deadline)
    return (parsed - timedelta(minutes=duration)).isoformat(timespec="seconds")


def _candidate_label(task: dict) -> str:
    title = task.get("title") or "未命名任务"
    task_date = task.get("date")
    deadline = task.get("deadline")
    if task_date:
        return f"{title}（{task_date}）"
    if deadline:
        return f"{title}（截止 {_format_datetime(deadline)}）"
    return title


def _format_datetime(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value


def _clarify(plan: dict, question: str) -> dict:
    plan["need_clarification"] = True
    plan["clarification_question"] = question
    return plan


def _result(success: bool, response_text: str, task: dict[str, Any] | None = None) -> dict:
    return {
        "success": success,
        "response_text": response_text,
        "task": task,
    }
