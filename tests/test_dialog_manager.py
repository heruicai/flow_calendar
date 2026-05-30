from src.dialog_manager import (
    apply_confirmed_action,
    build_confirmation_prompt,
    cancel_pending_action,
    create_pending_action,
    parse_confirmation_text,
    requires_confirmation,
)
from src.task_store import add_task, load_tasks


def test_add_event_generates_confirmation_prompt():
    parsed = {
        "intent": "add_event",
        "task": {
            "title": "算法面试",
            "date": "2026-05-31",
            "start_time": "15:00",
            "end_time": "16:00",
        },
    }

    prompt = build_confirmation_prompt(create_pending_action(parsed))

    assert "添加算法面试" in prompt
    assert "15:00到16:00" in prompt
    assert "确认或取消" in prompt


def test_parse_confirmation_text_recognizes_common_answers():
    assert parse_confirmation_text("确认") == "confirm"
    assert parse_confirmation_text("可以") == "confirm"
    assert parse_confirmation_text("是的") == "confirm"
    assert parse_confirmation_text("取消") == "cancel"
    assert parse_confirmation_text("不要") == "cancel"
    assert parse_confirmation_text("再想想") == "unknown"


def test_query_schedule_does_not_require_confirmation():
    assert requires_confirmation({"intent": "query_schedule"}) is False


def test_confirmed_add_action_returns_success_and_modifies_store(tmp_path):
    path = str(tmp_path / "tasks.json")
    pending = create_pending_action(
        {
            "intent": "add_event",
            "task": {"title": "算法面试", "type": "fixed_event", "date": "2026-05-31"},
        }
    )

    result = apply_confirmed_action(pending, path)

    assert result["success"] is True
    assert result["response_text"] == "已添加算法面试。"
    assert load_tasks(path)[0]["title"] == "算法面试"


def test_cancel_does_not_modify_store(tmp_path):
    path = str(tmp_path / "tasks.json")
    add_task({"title": "洗衣服", "type": "essential_task"}, path)
    before = load_tasks(path)

    result = cancel_pending_action()

    assert result["success"] is True
    assert result["response_text"] == "已取消本次操作。"
    assert load_tasks(path) == before
