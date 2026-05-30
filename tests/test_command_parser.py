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


def test_query_intent_has_priority_for_natural_questions():
    for command in (
        "我今天有什么安排",
        "明天有哪些任务",
        "查看明天日程",
        "查一下周五有什么事",
        "今天还剩什么",
    ):
        result = parse_command(command, now=NOW)
        assert result["intent"] == "query_schedule"


def test_parse_query_schedule_with_explicit_dates():
    assert parse_command("5月31日有什么安排", now=NOW)["query"]["date"] == "2026-05-31"
    assert parse_command("2026年5月31日有哪些任务", now=NOW)["query"]["date"] == "2026-05-31"
    assert parse_command("05-31有什么安排", now=NOW)["query"]["date"] == "2026-05-31"
    assert parse_command("2026-05-31有什么安排", now=NOW)["query"]["date"] == "2026-05-31"


def test_parse_query_schedule_with_next_weekday():
    result = parse_command("下周一有什么安排", now=NOW)

    assert result["intent"] == "query_schedule"
    assert result["query"]["date"] == "2026-06-01"


def test_fixed_event_without_end_time_defaults_to_one_hour():
    result = parse_command("明天下午三点面试", now=NOW)

    assert result["task"]["type"] == "fixed_event"
    assert result["task"]["start_time"] == "15:00"
    assert result["task"]["end_time"] == "16:00"
    assert "默认持续 1 小时" in result["parse_reason"]


def test_date_without_time_defaults_to_essential_task():
    result = parse_command("5月31日取快递", now=NOW)

    assert result["task"]["type"] == "essential_task"
    assert result["task"]["date"] == "2026-05-31"


def test_deadline_and_flexible_keywords_have_priority():
    deadline = parse_command("明晚前提交作业", now=NOW)
    flexible = parse_command("有空复习 kernelPCA", now=NOW)

    assert deadline["task"]["type"] == "deadline_task"
    assert deadline["task"]["latest_start_time"] is None
    assert flexible["task"]["type"] == "flexible_plan"
    assert flexible["task"]["display_mode"] == "todo_pool"


def test_natural_delete_and_complete_phrases():
    assert parse_command("把明天三点的面试删掉", now=NOW)["intent"] == "delete_event"
    assert parse_command("移除报告这个任务", now=NOW)["intent"] == "delete_event"
    assert parse_command("报告写完了", now=NOW)["intent"] == "mark_completed"


def test_parse_command_returns_confidence_and_reason():
    result = parse_command("我今天有什么安排", now=NOW)

    assert 0 <= result["confidence"] <= 1
    assert result["parse_reason"]


def test_update_fixed_event_time_inherits_target_date_and_period():
    result = parse_command("把明天下午三点的面试改到四点", now=NOW)

    assert result["intent"] == "update_event"
    assert result["target"]["keyword"] == "面试"
    assert result["updates"]["date"] == "2026-05-30"
    assert result["updates"]["start_time"] == "16:00"
    assert result["updates"]["end_time"] == "17:00"


def test_update_fixed_event_with_new_date_and_time_range():
    result = parse_command("把算法面试改成明天下午四点到五点", now=NOW)

    assert result["intent"] == "update_event"
    assert result["target"]["keyword"] == "算法面试"
    assert result["updates"]["date"] == "2026-05-30"
    assert result["updates"]["start_time"] == "16:00"
    assert result["updates"]["end_time"] == "17:00"


def test_update_deadline_task_with_weekday_deadline():
    result = parse_command("把报告截止时间改到周五晚上十一点", now=NOW)

    assert result["intent"] == "update_event"
    assert result["target"]["keyword"] == "报告"
    assert result["updates"]["deadline"] == "2026-06-05T23:00:00"


def test_update_deadline_task_with_tomorrow_evening_deadline():
    result = parse_command("把作业 deadline 改成明晚", now=NOW)

    assert result["intent"] == "update_event"
    assert result["target"]["keyword"] == "作业"
    assert result["updates"]["deadline"] == "2026-05-30T23:00:00"


def test_update_task_type():
    flexible = parse_command("把洗衣服改成弹性任务", now=NOW)
    essential = parse_command("把刷题改成今天必须做", now=NOW)
    deadline = parse_command("把报告改成截止任务", now=NOW)

    assert flexible["intent"] == "update_event"
    assert flexible["updates"]["type"] == "flexible_plan"
    assert flexible["updates"]["display_mode"] == "todo_pool"
    assert essential["intent"] == "update_event"
    assert essential["updates"]["type"] == "essential_task"
    assert essential["updates"]["display_mode"] == "essential_bar"
    assert deadline["updates"]["type"] == "deadline_task"
    assert "deadline" not in deadline["updates"]


def test_update_essential_task_date():
    result = parse_command("把洗衣服改到明天", now=NOW)

    assert result["intent"] == "update_event"
    assert result["target"]["keyword"] == "洗衣服"
    assert result["updates"]["date"] == "2026-05-30"


def test_update_without_change_details_requests_clarification():
    result = parse_command("改一下报告", now=NOW)

    assert result["intent"] == "update_event"
    assert result["need_clarification"] is True
    assert result["clarification_question"] == "你想修改任务的时间、截止时间，还是任务类型？"


def test_update_without_target_requests_clarification():
    result = parse_command("把那个任务改一下", now=NOW)

    assert result["intent"] == "update_event"
    assert result["need_clarification"] is True
    assert result["clarification_question"] == "你想修改哪个任务？"


def test_update_event_returns_confidence_and_reason():
    result = parse_command("把洗衣服改到明天", now=NOW)

    assert 0 <= result["confidence"] <= 1
    assert result["parse_reason"]
