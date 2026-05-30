"""Response generation helpers for FlowCal."""

from __future__ import annotations

from datetime import datetime


def build_welcome_message() -> str:
    """Return the default message shown before a command is submitted."""
    return "Record a voice command or use the text fallback to update FlowCal."


def build_schedule_summary(tasks: list[dict], selected_date: str) -> str:
    """Build a voice-friendly summary with concrete tasks for one date."""
    pending_sections = []
    completed_tasks = []

    fixed_tasks = _tasks_for_date(tasks, selected_date, "fixed_event")
    deadline_tasks = _deadline_tasks_for_date(tasks, selected_date)
    essential_tasks = _tasks_for_date(tasks, selected_date, "essential_task")
    flexible_tasks = [task for task in tasks if task.get("type") == "flexible_plan"]

    pending_fixed, completed_fixed = _partition_completed(fixed_tasks)
    pending_deadline, completed_deadline = _partition_completed(deadline_tasks)
    pending_essential, completed_essential = _partition_completed(essential_tasks)
    pending_flexible, completed_flexible = _partition_completed(flexible_tasks)
    completed_tasks.extend(completed_fixed + completed_deadline + completed_essential + completed_flexible)

    if pending_fixed:
        pending_sections.append("固定时间任务有" + "；".join(_format_fixed_task(task) for task in pending_fixed))
    if pending_deadline:
        pending_sections.append("截止任务有" + "；".join(_format_deadline_task(task) for task in pending_deadline))
    if pending_essential:
        pending_sections.append("生活必需任务有" + "；".join(_format_essential_task(task) for task in pending_essential))

    if pending_sections:
        summary = f"{selected_date} 有这些安排：" + "；".join(pending_sections) + "。"
    else:
        summary = f"{selected_date} 暂时没有已安排的固定任务、截止任务或生活必需任务。"

    if pending_flexible:
        titles = "、".join(_task_title(task) for task in pending_flexible)
        summary += f"待办池里还有{titles}，可以根据状态自行安排，不强制进入日历。"
    elif not pending_sections:
        summary += "待办池中如果有弹性任务，你可以自行安排。"

    if completed_tasks:
        titles = "、".join(_task_title(task) for task in completed_tasks)
        summary += f"已完成事项有{titles}。"
    return summary


def _tasks_for_date(tasks: list[dict], selected_date: str, task_type: str) -> list[dict]:
    return [
        task
        for task in tasks
        if task.get("type") == task_type and task.get("date") == selected_date
    ]


def _deadline_tasks_for_date(tasks: list[dict], selected_date: str) -> list[dict]:
    return [
        task
        for task in tasks
        if task.get("type") == "deadline_task"
        and str(task.get("deadline") or "").startswith(selected_date)
    ]


def _partition_completed(tasks: list[dict]) -> tuple[list[dict], list[dict]]:
    pending = [task for task in tasks if task.get("status") != "completed"]
    completed = [task for task in tasks if task.get("status") == "completed"]
    return pending, completed


def _format_fixed_task(task: dict) -> str:
    title = _task_title(task)
    start_time = task.get("start_time")
    end_time = task.get("end_time")
    if start_time and end_time:
        return f"{start_time}-{end_time} 的{title}"
    if start_time:
        return f"{start_time} 的{title}"
    return title


def _format_deadline_task(task: dict) -> str:
    details = [_task_title(task)]
    if task.get("deadline"):
        details.append(f"截止时间是{_format_datetime(task['deadline'])}")
    if task.get("estimated_duration_minutes"):
        details.append(f"预计需要{_format_duration(task['estimated_duration_minutes'])}")
    if task.get("latest_start_time"):
        details.append(f"最晚开始时间是{_format_datetime(task['latest_start_time'])}")
    return "，".join(details)


def _format_essential_task(task: dict) -> str:
    details = [_task_title(task)]
    if task.get("estimated_duration_minutes"):
        details.append(f"预计需要{_format_duration(task['estimated_duration_minutes'])}")
    elif task.get("preferred_time_window"):
        details.append(f"建议安排在{_format_time_window(task['preferred_time_window'])}")
    return "，".join(details)


def _format_datetime(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    return parsed.strftime("%Y-%m-%d %H:%M")


def _format_duration(minutes: int) -> str:
    if minutes % 60 == 0:
        return f"{minutes // 60} 小时"
    return f"{minutes} 分钟"


def _format_time_window(value: str) -> str:
    return {
        "morning": "上午",
        "afternoon": "下午",
        "evening": "晚上",
        "night": "夜间",
    }.get(value, value)


def _task_title(task: dict) -> str:
    return str(task.get("title") or "未命名任务")


def build_parse_response(parsed: dict) -> str:
    """Return a human-readable response for parser output."""
    if parsed.get("need_clarification"):
        return parsed.get("clarification_question") or "Please provide more details."

    response_text = parsed.get("response_text")
    if response_text:
        return response_text

    intent = parsed.get("intent")
    if intent == "add_event":
        task = parsed.get("task") or {}
        return f"Added task: {task.get('title', 'Untitled task')}"
    if intent == "query_schedule":
        date = (parsed.get("query") or {}).get("date")
        return f"Showing schedule for {date}."
    if intent == "delete_event":
        return "Delete command parsed."
    if intent == "mark_completed":
        return "Completion command parsed."
    return "Command parsed."
