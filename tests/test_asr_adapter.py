from types import SimpleNamespace

import pytest

from src.asr_adapter import ASRCandidate, MockASRAdapter, OptionalASRDependencyError, SenseVoiceASRAdapter, WhisperASRAdapter, create_asr_adapter
from src.voice_config import VoiceConfig
from src.voice_pipeline import transcribe_audio


def test_mock_adapter_returns_candidates_without_audio_runtime():
    candidates = [ASRCandidate("明天下午三点算法面试", 0.9, "mock")]

    assert MockASRAdapter(candidates).transcribe("unused.wav") == candidates


def test_adapter_factory_prefers_sensevoice_as_default():
    adapter = create_asr_adapter(VoiceConfig())

    assert isinstance(adapter, SenseVoiceASRAdapter)


def test_whisper_adapter_passes_accuracy_parameters(monkeypatch):
    captured = {}

    class Model:
        def transcribe(self, path, language=None, vad_filter=None, beam_size=None, temperature=None, initial_prompt=None, hotwords=None):
            captured.update(locals())
            return [SimpleNamespace(text="明天下午三点组会")], SimpleNamespace(language_probability=0.9)

    adapter = WhisperASRAdapter(VoiceConfig(whisper_model="large-v3-turbo"))
    monkeypatch.setattr(adapter, "_get_model", lambda: Model())

    adapter.transcribe("sample.wav", prompt="组会", hotwords=["组会"])

    assert captured["language"] == "zh"
    assert captured["beam_size"] == 5
    assert captured["temperature"] == 0
    assert captured["vad_filter"] is True
    assert captured["initial_prompt"] == "组会"


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
    assert result["fallback_asr_text"] == "明天下午三点算法面试"
    assert result["warnings"]


def test_sensevoice_missing_dependency_error_includes_install_hint(monkeypatch):
    adapter = SenseVoiceASRAdapter(VoiceConfig())
    monkeypatch.setitem(__import__("sys").modules, "funasr", None)

    with pytest.raises(OptionalASRDependencyError, match="pip install funasr modelscope"):
        adapter._get_model()
