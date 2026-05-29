from src.voice_adapter import (
    build_spoken_response,
    get_voice_input_mode_description,
    normalize_voice_text,
    text_to_speech,
)


def test_normalize_voice_text_handles_spaces_and_punctuation():
    text = " 嗯  明天 下午 三点, 提醒我复习。 "

    normalized = normalize_voice_text(text)

    assert normalized == "明天下午三点，提醒我复习"


def test_build_spoken_response_removes_markdown_and_truncates():
    response = "## Result\n**Added** task: `算法面试` " + "very long " * 30

    spoken = build_spoken_response(response)

    assert "#" not in spoken
    assert "*" not in spoken
    assert "`" not in spoken
    assert "Added" in spoken
    assert len(spoken) <= 140


def test_text_to_speech_mock_does_not_raise():
    result = text_to_speech("Added: 洗衣服")

    assert result["success"] is True
    assert result["mode"] == "mock"
    assert result["spoken_text"] == "Added: 洗衣服"
    assert result["message"]


def test_get_voice_input_mode_description_returns_text():
    description = get_voice_input_mode_description()

    assert description
    assert "simulated speech-to-text" in description
