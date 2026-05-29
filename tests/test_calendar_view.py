from src.calendar_view import get_task_style, group_tasks_for_view


def test_group_tasks_for_view_maps_types_to_categories():
    tasks = [
        {"id": "1", "type": "fixed_event", "date": "2026-05-30", "start_time": "09:00"},
        {"id": "2", "type": "essential_task", "date": "2026-05-30", "title": "洗衣服"},
        {"id": "3", "type": "deadline_task", "deadline": "2026-06-01T23:59:00"},
        {"id": "4", "type": "flexible_plan", "title": "阅读"},
    ]

    groups = group_tasks_for_view(tasks, "2026-05-30")

    assert groups["calendar_blocks"] == [tasks[0]]
    assert groups["essential_bars"] == [tasks[1]]
    assert groups["deadline_timeline"] == [tasks[2]]
    assert groups["todo_pool"] == [tasks[3]]


def test_completed_status_maps_to_gray_style():
    style = get_task_style({"type": "fixed_event", "status": "completed"})

    assert style["accent"] == "#6b7280"
    assert style["background"] == "#f3f4f6"
    assert style["is_completed"] == "true"


def test_deadline_task_does_not_enter_calendar_block():
    task = {"id": "deadline", "type": "deadline_task", "date": "2026-05-30"}

    groups = group_tasks_for_view([task], "2026-05-30")

    assert groups["calendar_blocks"] == []
    assert groups["deadline_timeline"] == [task]


def test_flexible_plan_enters_todo_pool_only():
    task = {"id": "flex", "type": "flexible_plan", "date": "2026-05-30"}

    groups = group_tasks_for_view([task], "2026-05-30")

    assert groups["calendar_blocks"] == []
    assert groups["todo_pool"] == [task]
