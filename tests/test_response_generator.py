from datetime import date, timedelta

from src.response_generator import build_schedule_summary
from src.voice_adapter import build_spoken_response


SELECTED_DATE = "2026-05-31"


def test_schedule_summary_includes_task_titles_and_fixed_time_range():
    tasks = [
        {
            "title": "算法面试",
            "type": "fixed_event",
            "date": SELECTED_DATE,
            "start_time": "15:00",
            "end_time": "16:00",
            "status": "pending",
        }
    ]

    summary = build_schedule_summary(tasks, SELECTED_DATE)

    assert "算法面试" in summary
    assert "15:00-16:00" in summary


def test_schedule_summary_includes_deadline_duration_and_latest_start():
    tasks = [
        {
            "title": "完成报告",
            "type": "deadline_task",
            "deadline": "2026-05-31T23:00:00",
            "estimated_duration_minutes": 180,
            "latest_start_time": "2026-05-31T20:00:00",
            "status": "pending",
        }
    ]

    summary = build_schedule_summary(tasks, SELECTED_DATE)

    assert "完成报告" in summary
    assert any(label in summary for label in ("今天截止", "明天截止", "查询当天截止"))
    assert "截止时间是2026-05-31 晚上11点" in summary
    assert "3 小时" in summary
    assert "最晚开始时间是2026-05-31 晚上8点" in summary


def test_schedule_summary_includes_ongoing_future_deadline_task():
    tasks = [
        {
            "title": "完成报告",
            "type": "deadline_task",
            "deadline": "2026-06-05T23:00:00",
            "estimated_duration_minutes": 180,
            "status": "pending",
        }
    ]

    summary = build_schedule_summary(tasks, SELECTED_DATE)

    assert "还有进行中的截止任务：完成报告" in summary
    assert "截止时间是2026-06-05 晚上11点" in summary
    assert "预计需要3 小时" in summary


def test_schedule_summary_marks_tomorrow_deadline_explicitly():
    tomorrow = date.today() + timedelta(days=1)
    deadline = f"{tomorrow.isoformat()}T23:00:00"

    summary = build_schedule_summary(
        [{"title": "提交申请", "type": "deadline_task", "deadline": deadline, "status": "pending"}],
        tomorrow.isoformat(),
    )

    assert "明天截止" in summary
    assert f"截止时间是{tomorrow.isoformat()} 晚上11点" in summary


def test_schedule_summary_marks_today_deadline_explicitly():
    today = date.today()
    deadline = f"{today.isoformat()}T23:00:00"

    summary = build_schedule_summary(
        [{"title": "提交申请", "type": "deadline_task", "deadline": deadline, "status": "pending"}],
        today.isoformat(),
    )

    assert "今天截止" in summary
    assert f"截止时间是{today.isoformat()} 晚上11点" in summary


def test_schedule_summary_includes_essential_duration_and_flexible_pool():
    tasks = [
        {
            "title": "洗衣服",
            "type": "essential_task",
            "date": SELECTED_DATE,
            "estimated_duration_minutes": 40,
            "status": "pending",
        },
        {
            "title": "刷两道 LeetCode",
            "type": "flexible_plan",
            "status": "pending",
        },
    ]

    summary = build_schedule_summary(tasks, SELECTED_DATE)

    assert "洗衣服" in summary
    assert "40 分钟" in summary
    assert "刷两道 LeetCode" in summary
    assert "不强制进入日历" in summary


def test_schedule_summary_marks_completed_tasks_separately():
    tasks = [
        {
            "title": "已完成会议",
            "type": "fixed_event",
            "date": SELECTED_DATE,
            "start_time": "10:00",
            "end_time": "11:00",
            "status": "completed",
        }
    ]

    summary = build_schedule_summary(tasks, SELECTED_DATE)

    assert "暂时没有已安排" in summary
    assert "已完成事项有已完成会议" in summary


def test_completed_deadline_task_is_not_a_pending_reminder():
    tasks = [
        {
            "title": "已完成报告",
            "type": "deadline_task",
            "deadline": "2026-05-31T23:00:00",
            "status": "completed",
        }
    ]

    summary = build_schedule_summary(tasks, SELECTED_DATE)

    assert "截止任务有已完成报告" not in summary
    assert "还有进行中的截止任务：已完成报告" not in summary
    assert "已完成事项有已完成报告" in summary


def test_spoken_schedule_reply_keeps_detailed_deadline_information():
    tasks = [
        {
            "title": "完成报告",
            "type": "deadline_task",
            "deadline": "2026-06-05T23:00:00",
            "estimated_duration_minutes": 180,
            "latest_start_time": "2026-06-05T20:00:00",
            "status": "pending",
        }
    ]

    text_reply = build_schedule_summary(tasks, SELECTED_DATE)
    spoken_reply = build_spoken_response(text_reply)

    assert "完成报告" in spoken_reply
    assert "截止时间是2026-06-05 晚上11点" in spoken_reply
    assert "预计需要3 小时" in spoken_reply
    assert "最晚开始时间是2026-06-05 晚上8点" in spoken_reply


def test_schedule_summary_handles_empty_day():
    summary = build_schedule_summary([], SELECTED_DATE)

    assert "暂时没有已安排的固定任务、截止任务或生活必需任务" in summary
