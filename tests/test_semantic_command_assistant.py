from datetime import datetime

from src.command_parser import parse_command
from src.semantic_command_assistant import (
    apply_update_plan,
    build_update_confirmation,
    build_update_plan,
    find_candidate_tasks,
)
from src.task_store import add_task, load_tasks


NOW = datetime(2026, 5, 29, 9, 0, 0)


def test_find_candidate_tasks_by_keyword():
    tasks = [{"id": "1", "title": "算法面试", "type": "fixed_event"}]

    assert find_candidate_tasks(tasks, "面试") == tasks


def test_build_update_plan_requests_clarification_for_duplicate_titles():
    tasks = [
        {"id": "1", "title": "面试", "type": "fixed_event", "date": "2026-05-30"},
        {"id": "2", "title": "面试", "type": "fixed_event", "date": "2026-06-01"},
    ]

    plan = build_update_plan(parse_command("把面试改到下午四点", now=NOW), tasks)

    assert plan["need_clarification"] is True
    assert "找到多个匹配任务" in plan["clarification_question"]
    assert "2026-05-30" in plan["clarification_question"]


def test_build_update_plan_prefers_type_implied_by_update():
    tasks = [
        {"id": "1", "title": "报告", "type": "flexible_plan"},
        {"id": "2", "title": "报告", "type": "deadline_task", "deadline": "2026-05-31T23:00:00"},
    ]

    plan = build_update_plan(parse_command("把报告截止时间改到周五晚上十一点", now=NOW), tasks)

    assert plan["need_clarification"] is False
    assert plan["matched_task"]["id"] == "2"


def test_build_update_plan_generates_fixed_event_updates():
    tasks = [
        {
            "id": "1",
            "title": "算法面试",
            "type": "fixed_event",
            "date": "2026-05-30",
            "start_time": "15:00",
            "end_time": "16:00",
        }
    ]

    plan = build_update_plan(parse_command("把算法面试改成明天下午四点到五点", now=NOW), tasks)

    assert plan["need_clarification"] is False
    assert plan["updates"]["date"] == "2026-05-30"
    assert plan["updates"]["start_time"] == "16:00"
    assert plan["updates"]["end_time"] == "17:00"


def test_build_update_plan_keeps_default_one_hour_fixed_event_duration():
    tasks = [
        {
            "id": "1",
            "title": "面试",
            "type": "fixed_event",
            "date": "2026-05-30",
            "start_time": "15:00",
            "end_time": "16:00",
        }
    ]

    plan = build_update_plan(parse_command("把明天下午三点的面试改到四点", now=NOW), tasks)

    assert plan["updates"]["start_time"] == "16:00"
    assert plan["updates"]["end_time"] == "17:00"


def test_build_update_plan_generates_deadline_updates():
    tasks = [{"id": "1", "title": "报告", "type": "deadline_task"}]

    plan = build_update_plan(parse_command("把报告截止时间改到周五晚上十一点", now=NOW), tasks)

    assert plan["need_clarification"] is False
    assert plan["updates"]["deadline"] == "2026-06-05T23:00:00"


def test_apply_update_plan_recalculates_latest_start_time(tmp_path):
    path = str(tmp_path / "tasks.json")
    task = add_task(
        {
            "title": "报告",
            "type": "deadline_task",
            "deadline": "2026-05-31T23:00:00",
            "estimated_duration_minutes": 180,
        },
        path,
    )
    plan = build_update_plan(
        parse_command("把报告截止时间改到周五晚上十一点", now=NOW),
        [task],
    )

    result = apply_update_plan(plan, path)

    assert result["success"] is True
    assert result["task"]["deadline"] == "2026-06-05T23:00:00"
    assert result["task"]["latest_start_time"] == "2026-06-05T20:00:00"


def test_build_update_plan_generates_essential_date_update():
    tasks = [{"id": "1", "title": "洗衣服", "type": "essential_task", "date": "2026-05-29"}]

    plan = build_update_plan(parse_command("把洗衣服改到明天", now=NOW), tasks)

    assert plan["need_clarification"] is False
    assert plan["updates"]["date"] == "2026-05-30"


def test_build_update_plan_generates_type_and_display_mode_updates():
    tasks = [{"id": "1", "title": "洗衣服", "type": "essential_task", "date": "2026-05-29"}]

    plan = build_update_plan(parse_command("把洗衣服改成弹性任务", now=NOW), tasks)

    assert plan["need_clarification"] is False
    assert plan["updates"]["type"] == "flexible_plan"
    assert plan["updates"]["display_mode"] == "todo_pool"


def test_build_update_plan_requires_schedule_for_fixed_event_conversion():
    tasks = [{"id": "1", "title": "面试", "type": "flexible_plan"}]

    plan = build_update_plan(parse_command("把面试改成固定时间任务", now=NOW), tasks)

    assert plan["need_clarification"] is True
    assert "日期、开始时间和结束时间" in plan["clarification_question"]


def test_build_update_plan_requires_deadline_for_deadline_conversion():
    tasks = [{"id": "1", "title": "报告", "type": "flexible_plan"}]

    plan = build_update_plan(parse_command("把报告改成截止任务", now=NOW), tasks)

    assert plan["need_clarification"] is True
    assert "截止时间" in plan["clarification_question"]


def test_build_update_plan_requests_clarification_when_task_is_missing():
    plan = build_update_plan(parse_command("把面试改到下午四点", now=NOW), [])

    assert plan["need_clarification"] is True
    assert "没有找到匹配任务" in plan["clarification_question"]


def test_apply_update_plan_writes_task_store(tmp_path):
    path = str(tmp_path / "tasks.json")
    task = add_task({"title": "洗衣服", "type": "essential_task", "date": "2026-05-29"}, path)
    plan = build_update_plan(parse_command("把洗衣服改到明天", now=NOW), [task])

    result = apply_update_plan(plan, path)

    assert result["success"] is True
    assert load_tasks(path)[0]["date"] == "2026-05-30"


def test_build_update_confirmation_describes_draft():
    tasks = [
        {
            "id": "1",
            "title": "面试",
            "type": "fixed_event",
            "date": "2026-05-30",
            "start_time": "15:00",
            "end_time": "16:00",
        }
    ]
    plan = build_update_plan(parse_command("把明天下午三点的面试改到四点", now=NOW), tasks)

    prompt = build_update_confirmation(plan)

    assert "我找到任务：面试" in prompt
    assert "16:00 到 17:00" in prompt
