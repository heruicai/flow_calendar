from types import SimpleNamespace

import pytest

from src.asr_adapter import ASRCandidate, LocalASRModelError, MockASRAdapter, OptionalASRDependencyError, SenseVoiceASRAdapter, WhisperASRAdapter, clean_sensevoice_text, create_asr_adapter
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

    adapter = WhisperASRAdapter(VoiceConfig(whisper_model="large-v3-turbo", whisper_allow_download=True))
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
        config=VoiceConfig(
            asr_engine="funasr",
            enable_dual_asr=True,
            asr_fallback_engine="whisper",
        ),
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


@pytest.mark.parametrize(
    ("raw_text", "cleaned_text"),
    [
        ("<|zh|><|NEUTRAL|>明天下午三点开组会", "明天下午三点开组会"),
        ("<|zh|><|HAPPY|><|Speech|>提醒我周五提交报告", "提醒我周五提交报告"),
        ("明天下午三点开组会", "明天下午三点开组会"),
    ],
)
def test_clean_sensevoice_text_removes_generic_metadata_tags(raw_text, cleaned_text):
    assert clean_sensevoice_text(raw_text) == cleaned_text


def test_sensevoice_adapter_preserves_raw_text_and_returns_clean_text(monkeypatch):
    adapter = SenseVoiceASRAdapter(VoiceConfig())
    monkeypatch.setattr(
        adapter,
        "_get_model",
        lambda: SimpleNamespace(
            generate=lambda **kwargs: [{"text": "<|zh|><|NEUTRAL|><|Speech|>明天下午三点开组会"}]
        ),
    )

    candidate = adapter.transcribe("sample.wav")[0]

    assert candidate.raw_text == "<|zh|><|NEUTRAL|><|Speech|>明天下午三点开组会"
    assert candidate.text == "明天下午三点开组会"
    assert candidate.metadata_tags_removed == ("zh", "NEUTRAL", "Speech")


def test_sensevoice_prefers_existing_local_model_path(monkeypatch, tmp_path):
    captured = {}
    monkeypatch.setitem(
        __import__("sys").modules,
        "funasr",
        SimpleNamespace(AutoModel=lambda **kwargs: captured.update(kwargs) or object()),
    )
    adapter = SenseVoiceASRAdapter(VoiceConfig(sensevoice_model_path=str(tmp_path)))

    adapter._get_model()

    assert captured == {"model": str(tmp_path), "disable_update": True}


def test_sensevoice_missing_local_path_does_not_download_by_default(tmp_path):
    adapter = SenseVoiceASRAdapter(VoiceConfig(sensevoice_model_path=str(tmp_path / "missing")))

    with pytest.raises(LocalASRModelError, match="VOICE_SENSEVOICE_ALLOW_DOWNLOAD=1"):
        adapter._get_model()


def test_whisper_missing_local_path_does_not_download_by_default(monkeypatch):
    adapter = WhisperASRAdapter(VoiceConfig())
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", None)

    with pytest.raises(LocalASRModelError, match="VOICE_WHISPER_ALLOW_DOWNLOAD=0"):
        adapter._get_model()
