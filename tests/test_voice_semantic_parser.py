from datetime import datetime

import pytest

from src.voice_understanding.semantic_parser import parse_semantic_frame


NOW = datetime(2026, 5, 31, 9, 0)


@pytest.mark.parametrize(
    ("text", "intent", "risk"),
    [
        ("\u660e\u5929\u4e0b\u5348\u4e09\u70b9\u7ec4\u4f1a", "add_event", "low"),
        ("\u6211\u660e\u5929\u6709\u4ec0\u4e48\u5b89\u6392", "query_schedule", "low"),
        ("\u5220\u9664\u660e\u5929\u7ec4\u4f1a", "delete_event", "high"),
        ("\u628a\u7ec4\u4f1a\u6539\u5230\u660e\u5929\u4e0b\u5348\u56db\u70b9", "update_event", "high"),
        ("\u7ec4\u4f1a\u5b8c\u6210\u4e86", "mark_completed", "medium"),
    ],
)
def test_semantic_parser_returns_uniform_frame(text, intent, risk):
    frame = parse_semantic_frame(text, now=NOW)

    assert frame.intent == intent
    assert frame.operation_risk == risk
    assert frame.normalized_text == text
