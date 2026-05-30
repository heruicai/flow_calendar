from __future__ import annotations

import json
from itertools import count

import src.task_store as task_store
from src.task_store import (
    add_task,
    delete_task,
    get_task_by_id,
    get_tasks_by_date,
    load_tasks,
    mark_task_completed,
    mark_task_pending,
    update_deadline_task,
    update_fixed_event_time,
    update_task_type,
)


def storage_path(tmp_path) -> str:
    return str(tmp_path / "tasks.json")


def test_add_task(tmp_path):
    path = storage_path(tmp_path)

    task = add_task(
        {
            "title": "算法面试",
            "type": "fixed_event",
            "date": "2026-05-30",
            "start_time": "15:00",
            "end_time": "16:00",
        },
        path,
    )

    assert task["id"]
    assert task["title"] == "算法面试"
    assert task["status"] == "pending"
    assert task["display_mode"] == "calendar_block"
    assert task["created_at"]
    assert task["updated_at"]


def test_load_tasks(tmp_path):
    path = storage_path(tmp_path)
    added = add_task({"title": "完成报告", "type": "deadline_task"}, path)

    tasks = load_tasks(path)

    assert len(tasks) == 1
    assert tasks[0]["id"] == added["id"]
    assert tasks[0]["title"] == "完成报告"


def test_get_tasks_by_date(tmp_path):
    path = storage_path(tmp_path)
    add_task({"title": "上午会议", "type": "fixed_event", "date": "2026-05-30"}, path)
    add_task({"title": "洗衣服", "type": "essential_task", "date": "2026-05-29"}, path)

    tasks = get_tasks_by_date("2026-05-29", path)

    assert len(tasks) == 1
    assert tasks[0]["title"] == "洗衣服"


def test_mark_task_completed(tmp_path):
    path = storage_path(tmp_path)
    task = add_task({"title": "买药", "type": "essential_task"}, path)

    completed = mark_task_completed(task["id"], path)

    assert completed is not None
    assert completed["status"] == "completed"
    assert completed["completed_at"]


def test_mark_task_pending_undoes_completion_and_updates_timestamp(tmp_path, monkeypatch):
    path = storage_path(tmp_path)
    seconds = count()
    monkeypatch.setattr(task_store, "_now_iso", lambda: f"2026-05-30T10:00:{next(seconds):02d}")
    task = add_task({"title": "Buy medicine", "type": "essential_task"}, path)
    completed = mark_task_completed(task["id"], path)

    pending = mark_task_pending(task["id"], path)

    assert pending is not None
    assert pending["status"] == "pending"
    assert pending["completed_at"] is None
    assert pending["updated_at"] > completed["updated_at"]


def test_delete_task(tmp_path):
    path = storage_path(tmp_path)
    task = add_task({"title": "刷两道 LeetCode", "type": "flexible_plan"}, path)

    assert delete_task(task["id"], path) is True
    assert get_task_by_id(task["id"], path) is None
    assert load_tasks(path) == []


def test_missing_tasks_file_does_not_raise(tmp_path):
    path = tmp_path / "missing" / "tasks.json"

    tasks = load_tasks(str(path))

    assert tasks == []
    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8")) == []


def test_update_fixed_event_time_persists_schedule_fields(tmp_path):
    path = storage_path(tmp_path)
    task = add_task(
        {
            "title": "Interview",
            "type": "fixed_event",
            "date": "2026-05-30",
            "start_time": "15:00",
            "end_time": "16:00",
        },
        path,
    )

    updated = update_fixed_event_time(task["id"], "2026-06-01", "09:00", "10:30", path)

    assert updated is not None
    assert updated["date"] == "2026-06-01"
    assert updated["start_time"] == "09:00"
    assert updated["end_time"] == "10:30"
    assert get_task_by_id(task["id"], path) == updated


def test_update_deadline_task_recalculates_latest_start(tmp_path):
    path = storage_path(tmp_path)
    task = add_task({"title": "Report", "type": "deadline_task"}, path)

    updated = update_deadline_task(task["id"], "2026-06-05T23:00:00", 180, path)

    assert updated is not None
    assert updated["deadline"] == "2026-06-05T23:00:00"
    assert updated["estimated_duration_minutes"] == 180
    assert updated["latest_start_time"] == "2026-06-05T20:00:00"


def test_update_task_type_sets_display_mode_and_essential_default_date(tmp_path):
    path = storage_path(tmp_path)
    task = add_task({"title": "Laundry", "type": "flexible_plan"}, path)

    updated = update_task_type(task["id"], "essential_task", selected_date="2026-06-01", path=path)

    assert updated is not None
    assert updated["type"] == "essential_task"
    assert updated["display_mode"] == "essential_bar"
    assert updated["date"] == "2026-06-01"


def test_update_task_type_sets_display_mode_for_each_target_type(tmp_path):
    path = storage_path(tmp_path)
    task = add_task({"title": "Plan", "type": "flexible_plan"}, path)

    fixed = update_task_type(
        task["id"],
        "fixed_event",
        updates={"date": "2026-06-01", "start_time": "09:00", "end_time": "10:00"},
        path=path,
    )
    deadline = update_task_type(
        task["id"],
        "deadline_task",
        updates={"deadline": "2026-06-02T18:00:00"},
        path=path,
    )
    essential = update_task_type(task["id"], "essential_task", selected_date="2026-06-03", path=path)
    flexible = update_task_type(task["id"], "flexible_plan", path=path)

    assert fixed["display_mode"] == "calendar_block"
    assert deadline["display_mode"] == "deadline_bar"
    assert essential["display_mode"] == "essential_bar"
    assert flexible["display_mode"] == "todo_pool"


def test_update_task_type_requires_fixed_event_schedule_fields(tmp_path):
    path = storage_path(tmp_path)
    task = add_task({"title": "Interview", "type": "flexible_plan"}, path)

    try:
        update_task_type(task["id"], "fixed_event", path=path)
    except ValueError as exc:
        assert "require date, start time, and end time" in str(exc)
    else:
        raise AssertionError("Expected incomplete fixed event conversion to fail.")


def test_update_task_type_requires_deadline(tmp_path):
    path = storage_path(tmp_path)
    task = add_task({"title": "Report", "type": "flexible_plan"}, path)

    try:
        update_task_type(task["id"], "deadline_task", path=path)
    except ValueError as exc:
        assert "require a deadline" in str(exc)
    else:
        raise AssertionError("Expected deadline conversion without a deadline to fail.")
