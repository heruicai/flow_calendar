from datetime import datetime

from src.command_parser import parse_command


NOW = datetime(2026, 5, 29, 9, 0, 0)


def test_parse_fixed_event():
    result = parse_command("明天下午三点到四点参加算法面试", now=NOW)

    assert result["intent"] == "add_event"
    assert result["need_clarification"] is False
    assert result["task"]["type"] == "fixed_event"
    assert result["task"]["date"] == "2026-05-30"
    assert result["task"]["start_time"] == "15:00"
    assert result["task"]["end_time"] == "16:00"
    assert result["task"]["display_mode"] == "calendar_block"
    assert "算法面试" in result["task"]["title"]


def test_parse_deadline_task_with_latest_start_time():
    result = parse_command("周五前完成报告，预计三小时", now=NOW)

    assert result["intent"] == "add_event"
    assert result["need_clarification"] is False
    assert result["task"]["type"] == "deadline_task"
    assert result["task"]["deadline"] == "2026-06-05T23:59:00"
    assert result["task"]["estimated_duration_minutes"] == 180
    assert result["task"]["latest_start_time"] == "2026-06-05T20:59:00"
    assert result["task"]["display_mode"] == "deadline_bar"


def test_parse_essential_task():
    result = parse_command("今天必须洗衣服", now=NOW)

    assert result["intent"] == "add_event"
    assert result["need_clarification"] is False
    assert result["task"]["type"] == "essential_task"
    assert result["task"]["date"] == "2026-05-29"
    assert result["task"]["display_mode"] == "essential_bar"


def test_parse_flexible_plan():
    result = parse_command("添加弹性任务，刷两道 LeetCode", now=NOW)

    assert result["intent"] == "add_event"
    assert result["need_clarification"] is False
    assert result["task"]["type"] == "flexible_plan"
    assert result["task"]["display_mode"] == "todo_pool"
    assert "LeetCode" in result["task"]["title"]


def test_parse_query_schedule():
    result = parse_command("我明天有什么安排", now=NOW)

    assert result["intent"] == "query_schedule"
    assert result["need_clarification"] is False
    assert result["query"]["date"] == "2026-05-30"


def test_parse_delete_event():
    result = parse_command("删除明天下午的算法面试", now=NOW)

    assert result["intent"] == "delete_event"
    assert result["need_clarification"] is False
    assert result["query"]["date"] == "2026-05-30"
    assert "算法面试" in result["query"]["keyword"]


def test_parse_mark_completed():
    result = parse_command("洗衣服完成了", now=NOW)

    assert result["intent"] == "mark_completed"
    assert result["need_clarification"] is False
    assert "洗衣服" in result["query"]["keyword"]


def test_parse_clarification_for_reminder_without_specific_time():
    result = parse_command("明天下午提醒我复习", now=NOW)

    assert result["intent"] == "add_event"
    assert result["need_clarification"] is True
    assert "具体时间" in result["clarification_question"]
