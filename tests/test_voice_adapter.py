from src import voice_adapter
from src.voice_adapter import build_spoken_response, normalize_voice_text, speech_to_text, text_to_speech


def test_normalize_voice_text_handles_spaces_punctuation_and_fillers():
    text = " 嗯 明天 下午 三点, 请帮我 复习。 "

    normalized = normalize_voice_text(text)

    assert normalized == "明天下午三点，复习"


def test_build_spoken_response_removes_markdown_without_truncating_details():
    response = "## Result\n**Added** task: `算法面试` " + "very long " * 30

    spoken = build_spoken_response(response)

    assert "#" not in spoken
    assert "*" not in spoken
    assert "`" not in spoken
    assert "Added" in spoken
    assert "very long" in spoken
    assert not spoken.endswith("...")


def test_text_to_speech_returns_controlled_error_when_tts_is_unavailable(monkeypatch):
    def raise_import_error():
        raise RuntimeError("tts unavailable")

    monkeypatch.setattr(voice_adapter, "_load_pyttsx3", raise_import_error)

    result = text_to_speech("已添加洗衣服。")

    assert result["success"] is False
    assert result["mode"] == "fallback"
    assert result["audio_path"] == ""
    assert "tts unavailable" in result["message"]


def test_speech_to_text_without_audio_returns_controlled_error():
    result = speech_to_text(None)

    assert result["success"] is False
    assert result["mode"] == "fallback"
    assert result["text"] == ""
    assert result["message"]


def test_normalize_voice_text_converts_common_traditional_chinese():
    normalized = normalize_voice_text("請確認這個語音任務，標記會議結束")

    assert normalized == "请确认这个语音任务，标记会议结束"


def test_spoken_response_uses_simplified_chinese():
    spoken = build_spoken_response("請確認語音任務，標記會議結束")

    assert spoken == "请确认语音任务，标记会议结束"
