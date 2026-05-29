from src.calendar_view import (
    build_day_timeline,
    build_month_calendar,
    get_task_indicators_for_date,
    get_task_style,
    group_tasks_for_view,
)


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
    assert indicators["essential_task"] == 1
    assert indicators["flexible_plan"] == 0
    assert indicators["completed"] == 1


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
