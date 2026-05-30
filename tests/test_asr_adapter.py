from types import SimpleNamespace

from src.asr_adapter import ASRCandidate, MockASRAdapter, WhisperASRAdapter, create_asr_adapter
from src.voice_config import VoiceConfig
from src.voice_pipeline import transcribe_audio


def test_mock_adapter_returns_candidates_without_audio_runtime():
    candidates = [ASRCandidate("明天下午三点算法面试", 0.9, "mock")]

    assert MockASRAdapter(candidates).transcribe("unused.wav") == candidates


def test_adapter_factory_keeps_whisper_as_default():
    adapter = create_asr_adapter(VoiceConfig())

    assert isinstance(adapter, WhisperASRAdapter)


def test_pipeline_reranks_and_returns_traceable_metadata():
    adapter = MockASRAdapter([ASRCandidate("提醒我明天下午三点蒜粉面试", 0.9, "mock")])

    result = transcribe_audio(
        "unused.wav",
        tasks=[{"title": "算法面试"}],
        adapter=adapter,
        config=VoiceConfig(),
    )

    assert result["text"] == "提醒我明天下午三点算法面试"
    assert result["raw_text"] == "提醒我明天下午三点蒜粉面试"
    assert result["corrections"]
    assert result["needs_confirmation"] is True


def test_optional_adapter_import_failure_falls_back_to_whisper(monkeypatch):
    class MissingOptionalAdapter:
        def transcribe(self, *args, **kwargs):
            raise ModuleNotFoundError("funasr")

    monkeypatch.setattr(
        WhisperASRAdapter,
        "transcribe",
        lambda self, *args, **kwargs: [ASRCandidate("明天下午三点算法面试", 0.9, "whisper")],
    )

    result = transcribe_audio(
        "unused.wav",
        adapter=MissingOptionalAdapter(),
        config=VoiceConfig(asr_engine="funasr"),
    )

    assert result["mode"] == "whisper"
    assert result["text"] == "明天下午三点算法面试"
