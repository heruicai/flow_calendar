from __future__ import annotations

import json

from src.task_store import (
    add_task,
    delete_task,
    get_task_by_id,
    get_tasks_by_date,
    load_tasks,
    mark_task_completed,
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
