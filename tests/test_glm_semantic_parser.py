import json
from datetime import datetime
from types import SimpleNamespace

import pytest

import src.glm_semantic_parser as glm_parser
from src.glm_semantic_parser import (
    build_glm_prompt,
    is_glm_parser_available,
    parse_user_command,
    parse_with_glm,
    validate_glm_parse_result,
)


NOW = datetime(2026, 5, 29, 9, 0, 0)


def _glm_result(intent, **overrides):
    result = {
        "intent": intent,
        "need_clarification": False,
        "clarification_question": "",
        "task": None,
        "query": {"date": None, "keyword": ""},
        "target": {},
        "updates": {},
        "confidence": 0.95,
        "parse_reason": "mock GLM parse",
        "response_text": "",
        "normalized_text": "",
        "corrections": [],
    }
    result.update(overrides)
    return result


def test_is_glm_parser_available_is_false_without_api_key(monkeypatch):
    monkeypatch.delenv("ZHIPU_API_KEY", raising=False)

    assert is_glm_parser_available() is False


def test_parse_user_command_falls_back_without_api_key(monkeypatch):
    monkeypatch.delenv("ZHIPU_API_KEY", raising=False)
    monkeypatch.setattr(
        glm_parser,
        "parse_with_glm",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not call GLM")),
    )

    result = parse_user_command("明天下午三点面试", now=NOW)

    assert result["source"] == "rule"
    assert result["intent"] == "add_event"
    assert result["normalized_text"] == "明天下午三点面试"


def test_parse_user_command_falls_back_for_invalid_json(monkeypatch):
    monkeypatch.setenv("ZHIPU_API_KEY", "test-key")
    monkeypatch.setattr(
        glm_parser,
        "parse_with_glm",
        lambda *args, **kwargs: (_ for _ in ()).throw(json.JSONDecodeError("bad", "x", 0)),
    )

    result = parse_user_command("明天有什么安排", now=NOW)

    assert result["source"] == "rule"
    assert result["intent"] == "query_schedule"


def test_parse_user_command_falls_back_for_invalid_intent(monkeypatch):
    monkeypatch.setenv("ZHIPU_API_KEY", "test-key")
    monkeypatch.setattr(glm_parser, "parse_with_glm", lambda *args, **kwargs: _glm_result("unsupported"))

    result = parse_user_command("明天有什么安排", now=NOW)

    assert result["source"] == "rule"
    assert result["intent"] == "query_schedule"


def test_validate_glm_parse_result_accepts_valid_json():
    result = validate_glm_parse_result(
        _glm_result("query_schedule", query={"date": "2026-05-30", "keyword": ""})
    )

    assert result["source"] == "glm"
    assert result["confidence"] == 0.95


def test_parse_user_command_returns_glm_source_for_query(monkeypatch):
    monkeypatch.setenv("ZHIPU_API_KEY", "test-key")
    monkeypatch.setattr(
        glm_parser,
        "parse_with_glm",
        lambda *args, **kwargs: _glm_result(
            "query_schedule",
            query={"date": "2026-05-30", "keyword": ""},
        ),
    )

    result = parse_user_command("明天有什么安排", now=NOW)

    assert result["source"] == "glm"
    assert result["query"]["date"] == "2026-05-30"


def test_parse_user_command_accepts_glm_update_event(monkeypatch):
    monkeypatch.setenv("ZHIPU_API_KEY", "test-key")
    monkeypatch.setattr(
        glm_parser,
        "parse_with_glm",
        lambda *args, **kwargs: _glm_result(
            "update_event",
            target={"keyword": "面试"},
            updates={"date": "2026-05-30", "start_time": "16:00", "end_time": "17:00"},
        ),
    )

    result = parse_user_command("把面试改到明天下午四点", now=NOW)

    assert result["source"] == "glm"
    assert result["updates"]["start_time"] == "16:00"


def test_parse_user_command_returns_corrected_glm_text(monkeypatch):
    monkeypatch.setenv("ZHIPU_API_KEY", "test-key")
    monkeypatch.setattr(
        glm_parser,
        "parse_with_glm",
        lambda *args, **kwargs: _glm_result(
            "update_event",
            target={"keyword": "算法面试"},
            updates={"date": "2026-05-30", "start_time": "16:00", "end_time": "17:00"},
            normalized_text="把算法面试改到明天下午四点",
            corrections=[
                {
                    "from": "蒜粉面试",
                    "to": "算法面试",
                    "reason": "结合已有任务标题修正 ASR 误识别",
                }
            ],
        ),
    )

    result = parse_user_command("把蒜粉面试改到明天下午四点", now=NOW)

    assert result["normalized_text"] == "把算法面试改到明天下午四点"
    assert result["corrections"][0]["to"] == "算法面试"


def test_validate_glm_parse_result_rejects_invalid_corrections():
    with pytest.raises(ValueError, match="corrections"):
        validate_glm_parse_result(
            _glm_result(
                "query_schedule",
                query={"date": "2026-05-30", "keyword": ""},
                corrections="not-a-list",
            )
        )


def test_parse_user_command_accepts_glm_add_event(monkeypatch):
    monkeypatch.setenv("ZHIPU_API_KEY", "test-key")
    monkeypatch.setattr(
        glm_parser,
        "parse_with_glm",
        lambda *args, **kwargs: _glm_result(
            "add_event",
            task={
                "title": "面试",
                "type": "fixed_event",
                "date": "2026-05-30",
                "start_time": "15:00",
                "end_time": "16:00",
                "display_mode": "calendar_block",
            },
        ),
    )

    result = parse_user_command("明天下午三点面试", now=NOW)

    assert result["source"] == "glm"
    assert result["task"]["type"] == "fixed_event"


def test_low_confidence_glm_result_falls_back_to_rules(monkeypatch):
    monkeypatch.setenv("ZHIPU_API_KEY", "test-key")
    monkeypatch.setattr(
        glm_parser,
        "parse_with_glm",
        lambda *args, **kwargs: _glm_result(
            "query_schedule",
            query={"date": "2099-01-01", "keyword": ""},
            confidence=0.2,
        ),
    )

    result = parse_user_command("明天有什么安排", now=NOW)

    assert result["source"] == "rule"
    assert result["query"]["date"] == "2026-05-30"


def test_parse_with_glm_uses_mock_client_and_rejects_invalid_json(monkeypatch):
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))]
    )
    completions = SimpleNamespace(create=lambda **kwargs: response)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    monkeypatch.setattr(glm_parser, "_create_glm_client", lambda: client)

    with pytest.raises(json.JSONDecodeError):
        parse_with_glm("明天有什么安排", now=NOW)


def test_prompt_sends_only_minimal_task_context():
    prompt = build_glm_prompt(
        "把报告改到明天",
        now=NOW,
        tasks=[
            {
                "id": "private-id",
                "title": "报告",
                "date": "2026-05-30",
                "type": "deadline_task",
                "status": "pending",
                "notes": "private notes",
            }
        ],
    )

    assert '"title": "报告"' in prompt
    assert '"status": "pending"' in prompt
    assert "private-id" not in prompt
    assert "private notes" not in prompt
