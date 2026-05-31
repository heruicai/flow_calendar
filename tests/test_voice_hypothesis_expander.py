import pytest

from src.voice_understanding.hypothesis_expander import expand_hypotheses


def test_expander_generates_context_supported_title_candidate_without_overwriting_original():
    values = expand_hypotheses("\u660e\u5929\u4e0b\u5348\u4e09\u70b9\u849c\u7c89\u9762\u8bd5", context_terms=["\u7b97\u6cd5\u9762\u8bd5"])

    assert values[0].text == "\u660e\u5929\u4e0b\u5348\u4e09\u70b9\u849c\u7c89\u9762\u8bd5"
    assert any(item.text.endswith("\u7b97\u6cd5\u9762\u8bd5") for item in values)


def test_expander_generates_time_slot_candidate_for_homophone():
    values = expand_hypotheses("\u660e\u5929\u4e0b\u5348\u53c2\u70b9\u7ec4\u4f1a")

    assert any("\u4e09\u70b9" in item.text for item in values)


@pytest.mark.parametrize("title", ["\u53c2\u6570\u5b66\u4e60", "\u53c2\u52a0\u9879\u76ee\u4f1a", "\u4e09\u4f53\u8bfb\u4e66\u4f1a", "\u7b2c\u4e09\u7ae0\u590d\u4e60"])
def test_expander_preserves_original_title_as_first_candidate(title):
    assert expand_hypotheses(title)[0].text == title
