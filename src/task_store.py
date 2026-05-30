"""JSON-backed task storage for FlowCal."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4


DEFAULT_TASKS_PATH = Path("data/tasks.json")
SAMPLE_TASKS_PATH = Path("data/sample_tasks.json")

TASK_TYPES = {
    "fixed_event",
    "deadline_task",
    "essential_task",
    "flexible_plan",
}

TASK_STATUSES = {
    "pending",
    "completed",
    "postponed",
    "cancelled",
}

DISPLAY_MODES_BY_TYPE = {
    "fixed_event": "calendar_block",
    "deadline_task": "deadline_bar",
    "essential_task": "essential_bar",
    "flexible_plan": "todo_pool",
}

TASK_FIELDS = {
    "id": None,
    "title": "",
    "type": "flexible_plan",
    "date": None,
    "start_time": None,
    "end_time": None,
    "deadline": None,
    "estimated_duration_minutes": None,
    "latest_start_time": None,
    "preferred_time_window": None,
    "status": "pending",
    "created_at": None,
    "updated_at": None,
    "completed_at": None,
    "display_mode": "todo_pool",
    "notes": "",
}


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _resolve_path(path: str | None = None) -> Path:
    return Path(path) if path else DEFAULT_TASKS_PATH


def _ensure_storage_file(path: Path) -> None:
    if path.exists():
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[]\n", encoding="utf-8")


def _normalize_task(task: dict[str, Any], *, is_new: bool = False) -> dict[str, Any]:
    now = _now_iso()
    has_display_mode = bool(task.get("display_mode"))
    normalized = deepcopy(TASK_FIELDS)
    normalized.update(task)

    if not normalized["id"]:
        normalized["id"] = uuid4().hex

    if normalized["type"] not in TASK_TYPES:
        normalized["type"] = "flexible_plan"

    if normalized["status"] not in TASK_STATUSES:
        normalized["status"] = "pending"

    if not has_display_mode:
        normalized["display_mode"] = DISPLAY_MODES_BY_TYPE[normalized["type"]]

    if not normalized.get("created_at"):
        normalized["created_at"] = now

    if is_new or not normalized.get("updated_at"):
        normalized["updated_at"] = now

    return normalized


def load_tasks(path: str | None = None) -> list:
    """Load tasks from JSON storage.

    Missing files are initialized with an empty task list. Invalid or damaged
    JSON returns an empty list so UI flows can continue without crashing.
    """
    storage_path = _resolve_path(path)

    try:
        _ensure_storage_file(storage_path)
        raw_data = json.loads(storage_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(raw_data, list):
        return []

    return [task for task in raw_data if isinstance(task, dict)]


def save_tasks(tasks: list, path: str | None = None) -> None:
    """Persist tasks to JSON storage."""
    storage_path = _resolve_path(path)

    try:
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_text(
            json.dumps(tasks, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        return


def add_task(task: dict, path: str | None = None) -> dict:
    """Add a task and return the stored task."""
    tasks = load_tasks(path)
    new_task = _normalize_task(task, is_new=True)
    tasks.append(new_task)
    save_tasks(tasks, path)
    return new_task


def update_task(task_id: str, updates: dict, path: str | None = None) -> dict | None:
    """Update a task by id and return the updated task."""
    tasks = load_tasks(path)

    for index, task in enumerate(tasks):
        if task.get("id") != task_id:
            continue

        updated_task = deepcopy(task)
        updated_task.update(updates)
        updated_task["id"] = task_id
        updated_task["updated_at"] = _now_iso()
        updated_task = _normalize_task(updated_task)
        tasks[index] = updated_task
        save_tasks(tasks, path)
        return updated_task

    return None


def delete_task(task_id: str, path: str | None = None) -> bool:
    """Delete a task by id."""
    tasks = load_tasks(path)
    remaining_tasks = [task for task in tasks if task.get("id") != task_id]

    if len(remaining_tasks) == len(tasks):
        return False

    save_tasks(remaining_tasks, path)
    return True


def get_task_by_id(task_id: str, path: str | None = None) -> dict | None:
    """Return one task by id."""
    for task in load_tasks(path):
        if task.get("id") == task_id:
            return task

    return None


def get_tasks_by_date(date: str, path: str | None = None) -> list:
    """Return tasks assigned to a specific date."""
    return [task for task in load_tasks(path) if task.get("date") == date]


def get_pending_tasks(path: str | None = None) -> list:
    """Return tasks that are still pending."""
    return [task for task in load_tasks(path) if task.get("status") == "pending"]


def mark_task_completed(task_id: str, path: str | None = None) -> dict | None:
    """Mark a task as completed and set completion time."""
    now = _now_iso()
    return update_task(
        task_id,
        {
            "status": "completed",
            "completed_at": now,
        },
        path,
    )


def mark_task_pending(task_id: str, path: str | None = None) -> dict | None:
    """Undo task completion and return the task to its pending state."""
    return update_task(
        task_id,
        {
            "status": "pending",
            "completed_at": None,
        },
        path,
    )


def mark_task_postponed(
    task_id: str,
    new_date: str,
    path: str | None = None,
) -> dict | None:
    """Postpone a task to a new date."""
    return update_task(
        task_id,
        {
            "status": "postponed",
            "date": new_date,
        },
        path,
    )


def update_fixed_event_time(
    task_id: str,
    event_date: str,
    start_time: str,
    end_time: str,
    path: str | None = None,
) -> dict | None:
    """Update a fixed event after validating its required schedule fields."""
    event_date, start_time, end_time = _validated_fixed_event_schedule(event_date, start_time, end_time)
    return update_task(
        task_id,
        {
            "date": event_date,
            "start_time": start_time,
            "end_time": end_time,
        },
        path,
    )


def update_deadline_task(
    task_id: str,
    deadline: str,
    estimated_duration_minutes: int | None = None,
    path: str | None = None,
) -> dict | None:
    """Update a deadline task and derive its latest viable start time."""
    if not deadline:
        raise ValueError("Deadline tasks require a deadline.")
    try:
        parsed_deadline = datetime.fromisoformat(deadline)
    except ValueError as exc:
        raise ValueError("Deadline must be a valid ISO datetime.") from exc

    duration = estimated_duration_minutes or None
    latest_start_time = None
    if duration:
        if duration < 0:
            raise ValueError("Estimated duration cannot be negative.")
        latest_start_time = (parsed_deadline - timedelta(minutes=duration)).isoformat(timespec="seconds")

    return update_task(
        task_id,
        {
            "deadline": parsed_deadline.isoformat(timespec="seconds"),
            "estimated_duration_minutes": duration,
            "latest_start_time": latest_start_time,
        },
        path,
    )


def update_task_type(
    task_id: str,
    task_type: str,
    *,
    selected_date: str | None = None,
    updates: dict[str, Any] | None = None,
    path: str | None = None,
) -> dict | None:
    """Change task type while preserving the target type's data invariants."""
    if task_type not in TASK_TYPES:
        raise ValueError(f"Unsupported task type: {task_type}")

    current_task = get_task_by_id(task_id, path)
    if not current_task:
        return None

    target = deepcopy(current_task)
    target.update(updates or {})
    target["type"] = task_type
    target["display_mode"] = DISPLAY_MODES_BY_TYPE[task_type]

    if task_type == "fixed_event":
        event_date, start_time, end_time = _validated_fixed_event_schedule(
            target.get("date"),
            target.get("start_time"),
            target.get("end_time"),
        )
        target.update({"date": event_date, "start_time": start_time, "end_time": end_time})
        target.update({"deadline": None, "latest_start_time": None})
    elif task_type == "deadline_task":
        if not target.get("deadline"):
            raise ValueError("Deadline tasks require a deadline.")
        target.update({"date": None, "start_time": None, "end_time": None})
        parsed_deadline = datetime.fromisoformat(target["deadline"])
        duration = target.get("estimated_duration_minutes")
        target["latest_start_time"] = (
            (parsed_deadline - timedelta(minutes=duration)).isoformat(timespec="seconds")
            if duration
            else None
        )
    elif task_type == "essential_task":
        target.update(
            {
                "date": target.get("date") or selected_date,
                "start_time": None,
                "end_time": None,
                "deadline": None,
                "latest_start_time": None,
            }
        )
        if not target["date"]:
            raise ValueError("Essential tasks require a date.")
    else:
        target.update(
            {
                "date": None,
                "start_time": None,
                "end_time": None,
                "deadline": None,
                "latest_start_time": None,
            }
        )

    return update_task(task_id, target, path)


def _validated_fixed_event_schedule(
    event_date: str | None,
    start_time: str | None,
    end_time: str | None,
) -> tuple[str, str, str]:
    if not event_date or not start_time or not end_time:
        raise ValueError("Fixed events require date, start time, and end time.")
    try:
        normalized_date = date.fromisoformat(event_date).isoformat()
        normalized_start = datetime.strptime(start_time, "%H:%M").strftime("%H:%M")
        normalized_end = datetime.strptime(end_time, "%H:%M").strftime("%H:%M")
    except ValueError as exc:
        raise ValueError("Fixed event date or time format is invalid.") from exc
    if normalized_start >= normalized_end:
        raise ValueError("Fixed event end time must be after its start time.")
    return normalized_date, normalized_start, normalized_end
