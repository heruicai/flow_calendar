from src.asr_adapter import ASRCandidate, MockASRAdapter
from src.voice_config import VoiceConfig, get_voice_config
from src.voice_pipeline import transcribe_audio


def test_cloud_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("VOICE_ALLOW_CLOUD", raising=False)
    assert get_voice_config().allow_cloud is False


def test_product_voice_pipeline_never_calls_legacy_glm_even_when_keys_exist(monkeypatch):
    monkeypatch.setenv("ZHIPU_API_KEY", "must-not-be-used")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-used")

    def fail(*args, **kwargs):
        raise AssertionError("cloud parser must not run")

    monkeypatch.setattr("src.glm_semantic_parser.parse_with_glm", fail)
    result = transcribe_audio(
        "unused.wav",
        adapter=MockASRAdapter([ASRCandidate("\u660e\u5929\u4e0b\u5348\u4e09\u70b9\u7ec4\u4f1a", 0.9, "mock")]),
        config=VoiceConfig(enable_trace=False),
    )

    assert result["semantic_frame"]["intent"] == "add_event"


def test_mock_product_pipeline_does_not_open_network_connections(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("network access must not occur")

    monkeypatch.setattr("socket.create_connection", fail)
    result = transcribe_audio(
        "unused.wav",
        adapter=MockASRAdapter([ASRCandidate("\u660e\u5929\u4e0b\u5348\u4e09\u70b9\u7ec4\u4f1a", 0.9, "mock")]),
        config=VoiceConfig(enable_trace=False),
    )

    assert result["semantic_frame"]["intent"] == "add_event"
