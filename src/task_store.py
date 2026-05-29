"""JSON-backed task storage for FlowCal."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
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
