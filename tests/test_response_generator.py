from src.response_generator import build_schedule_summary


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
    assert "2026-05-31 23:00" in summary
    assert "3 小时" in summary
    assert "2026-05-31 20:00" in summary


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


def test_schedule_summary_handles_empty_day():
    summary = build_schedule_summary([], SELECTED_DATE)

    assert "暂时没有已安排的固定任务、截止任务或生活必需任务" in summary
