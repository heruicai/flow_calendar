from src import calendar_view
from src.calendar_view import (
    build_day_timeline,
    build_month_calendar,
    get_task_indicators_for_date,
    get_task_style,
    group_tasks_for_view,
    render_day_timeline,
)
from src.task_store import add_task, load_tasks, update_fixed_event_time, update_task_type


def test_build_month_calendar_returns_week_structure():
    weeks = build_month_calendar(2026, 5, [])

    assert len(weeks) in {5, 6}
    assert all(len(week) == 7 for week in weeks)
    assert any(day["date"] == "2026-05-01" for week in weeks for day in week)
    assert any(day["date"] == "2026-05-31" for week in weeks for day in week)


def test_get_task_indicators_for_date_counts_types_and_completed():
    tasks = [
        {"id": "1", "type": "fixed_event", "date": "2026-05-30", "status": "pending"},
        {"id": "2", "type": "essential_task", "date": "2026-05-30", "status": "completed"},
        {"id": "3", "type": "deadline_task", "deadline": "2026-05-30T18:00:00", "status": "pending"},
        {"id": "4", "type": "flexible_plan", "date": "2026-05-30", "status": "pending"},
    ]

    indicators = get_task_indicators_for_date(tasks, "2026-05-30")

    assert indicators["fixed_event"] == 1
    assert indicators["deadline_task"] == 1
    assert indicators["essential_task"] == 0
    assert indicators["flexible_plan"] == 0
    assert indicators["completed"] == 1


def test_completed_essential_tasks_move_from_pending_to_gray_indicator():
    tasks = [
        {"id": "1", "type": "essential_task", "date": "2026-05-30", "status": "completed"},
        {"id": "2", "type": "essential_task", "date": "2026-05-30", "status": "completed"},
        {"id": "3", "type": "essential_task", "date": "2026-05-30", "status": "completed"},
    ]

    indicators = get_task_indicators_for_date(tasks, "2026-05-30")

    assert indicators["essential_task"] == 0
    assert indicators["completed"] == 3


def test_fixed_event_uses_start_and_end_time_in_day_timeline():
    task = {
        "id": "fixed",
        "title": "算法面试",
        "type": "fixed_event",
        "date": "2026-05-30",
        "start_time": "15:00",
        "end_time": "16:00",
    }

    entries = build_day_timeline([task], "2026-05-30")

    assert len(entries) == 1
    assert entries[0]["start_time"] == "15:00"
    assert entries[0]["end_time"] == "16:00"
    assert entries[0]["task"] == task


def test_deadline_task_uses_midnight_to_deadline_on_due_date():
    task = {
        "id": "deadline",
        "title": "完成报告",
        "type": "deadline_task",
        "deadline": "2026-05-30T18:00:00",
        "estimated_duration_minutes": 180,
        "latest_start_time": "2026-05-30T15:00:00",
    }

    entries = build_day_timeline([task], "2026-05-30")

    assert len(entries) == 1
    assert entries[0]["start_time"] == "00:00"
    assert entries[0]["end_time"] == "18:00"


def test_essential_task_defaults_to_daytime_range():
    task = {
        "id": "essential",
        "title": "洗衣服",
        "type": "essential_task",
        "date": "2026-05-30",
    }

    entries = build_day_timeline([task], "2026-05-30")

    assert len(entries) == 1
    assert entries[0]["start_time"] == "07:00"
    assert entries[0]["end_time"] == "22:00"


def test_flexible_plan_does_not_enter_day_timeline():
    task = {"id": "flex", "type": "flexible_plan", "date": "2026-05-30"}

    entries = build_day_timeline([task], "2026-05-30")
    groups = group_tasks_for_view([task], "2026-05-30")

    assert entries == []
    assert groups["todo_pool"] == [task]


def test_completed_status_maps_to_gray_style():
    style = get_task_style({"type": "fixed_event", "status": "completed"})

    assert style["accent"] == "#6b7280"
    assert style["background"] == "#f3f4f6"
    assert style["is_completed"] == "true"


def test_day_timeline_renders_actions_for_each_specific_task(monkeypatch):
    tasks = [
        {
            "id": "fixed-1",
            "title": "Interview",
            "type": "fixed_event",
            "date": "2026-05-30",
            "start_time": "15:00",
            "end_time": "16:00",
        },
        {
            "id": "essential-1",
            "title": "Laundry",
            "type": "essential_task",
            "date": "2026-05-30",
        },
    ]
    rendered_task_ids = []
    monkeypatch.setattr(calendar_view, "_render_calendar_styles", lambda: None)
    monkeypatch.setattr(calendar_view.st, "markdown", lambda *args, **kwargs: None)

    render_day_timeline(
        tasks,
        "2026-05-30",
        action_renderer=lambda task: rendered_task_ids.append(task["id"]),
    )

    assert rendered_task_ids == ["essential-1", "fixed-1"]


def test_type_change_to_flexible_plan_removes_task_from_day_timeline(tmp_path):
    path = str(tmp_path / "tasks.json")
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

    update_task_type(task["id"], "flexible_plan", path=path)
    tasks = load_tasks(path)

    assert build_day_timeline(tasks, "2026-05-30") == []
    assert group_tasks_for_view(tasks, "2026-05-30")["todo_pool"][0]["id"] == task["id"]


def test_type_change_to_essential_task_enters_selected_day_timeline(tmp_path):
    path = str(tmp_path / "tasks.json")
    task = add_task({"title": "Laundry", "type": "flexible_plan"}, path)

    update_task_type(task["id"], "essential_task", selected_date="2026-05-30", path=path)
    entries = build_day_timeline(load_tasks(path), "2026-05-30")

    assert [entry["task_id"] for entry in entries] == [task["id"]]


def test_fixed_event_time_update_moves_month_indicator(tmp_path):
    path = str(tmp_path / "tasks.json")
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

    update_fixed_event_time(task["id"], "2026-05-31", "09:00", "10:00", path)
    tasks = load_tasks(path)

    assert get_task_indicators_for_date(tasks, "2026-05-30")["fixed_event"] == 0
    assert get_task_indicators_for_date(tasks, "2026-05-31")["fixed_event"] == 1
