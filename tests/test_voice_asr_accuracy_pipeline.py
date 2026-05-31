import shutil
import sys
import wave
from types import SimpleNamespace

from src.asr_adapter import ASRCandidate, MockASRAdapter, WhisperASRAdapter
from src.voice_config import VoiceConfig
from src.voice_pipeline import transcribe_audio
from src.voice_understanding.asr_comparison import compare_asr_candidates
from src.voice_understanding.pipeline import understand_voice


def test_dynamic_prompt_is_injected_into_local_adapter():
    captured = {}

    class Adapter:
        def transcribe(self, audio_path, *, prompt="", hotwords=None):
            captured["prompt"] = prompt
            captured["hotwords"] = hotwords
            return [ASRCandidate("明天下午三点组会", 0.9, "mock")]

    transcribe_audio(
        "unused.wav",
        tasks=[{"title": "季度复盘"}],
        adapter=Adapter(),
        config=VoiceConfig(enable_trace=False, enable_asr_diagnostics=False),
    )

    assert "季度复盘" in captured["prompt"]
    assert "季度复盘" in captured["hotwords"]


def test_diagnostics_include_required_accuracy_fields(capsys):
    result = transcribe_audio(
        "unused.wav",
        adapter=MockASRAdapter([ASRCandidate("明天下午三点组会", 0.9, "mock")]),
        config=VoiceConfig(enable_trace=False),
    )

    output = capsys.readouterr().out
    diagnostic = result["asr_diagnostics"][0]
    assert "[flowcal-asr]" in output
    assert diagnostic["engine"] == "mock"
    assert set(diagnostic) == {
        "engine", "model", "model_path", "language", "beam_size", "vad_enabled",
        "initial_prompt_injected", "torchaudio_available", "ffmpeg_available",
        "dual_asr_enabled", "fallback_engine", "fallback_used", "audio_duration",
        "raw_text", "cleaned_text", "metadata_tags_removed", "fallback_asr_text", "warning",
    }


def test_divergent_asr_outputs_require_confirmation():
    result = transcribe_audio(
        "unused.wav",
        adapter=MockASRAdapter([
            ASRCandidate("明天下午三点组会", 0.9, "sensevoice"),
            ASRCandidate("明天下午七点取快递", 0.9, "whisper"),
        ]),
        config=VoiceConfig(enable_trace=False, enable_asr_diagnostics=False),
    )

    assert result["asr_comparison"]["requires_confirmation"] is True
    assert result["decision"]["action"] == "confirm"


def test_similar_asr_outputs_can_continue_normally():
    comparison = compare_asr_candidates([
        ASRCandidate("明天下午三点组会", 0.9, "sensevoice"),
        ASRCandidate("明天下午三点组会。", 0.9, "whisper"),
    ])

    assert comparison["requires_confirmation"] is False
    assert comparison["similarity"] == 1.0


def test_diagnostic_audio_duration_comes_from_local_wav_metadata(tmp_path):
    audio_path = tmp_path / "one-second.wav"
    with wave.open(str(audio_path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(8000)
        stream.writeframes(b"\x00\x00" * 8000)

    result = understand_voice(
        audio_path,
        adapter=MockASRAdapter([ASRCandidate("明天下午三点组会", 0.9, "mock")]),
        config=VoiceConfig(enable_trace=False, enable_asr_diagnostics=False),
    )

    assert result.asr_diagnostics[0]["audio_duration"] == 1.0


def test_non_wav_audio_duration_uses_local_soundfile_metadata(monkeypatch, tmp_path):
    audio_path = tmp_path / "sample.mp3"
    audio_path.write_bytes(b"local-audio-placeholder")
    monkeypatch.setitem(
        sys.modules,
        "soundfile",
        SimpleNamespace(info=lambda path: SimpleNamespace(duration=5.622, samplerate=48000, channels=1)),
    )

    result = understand_voice(
        audio_path,
        adapter=MockASRAdapter([ASRCandidate("明天下午三点组会", 0.9, "mock")]),
        config=VoiceConfig(enable_trace=False, enable_asr_diagnostics=False),
    )

    assert result.asr_diagnostics[0]["audio_duration"] == 5.622


def test_default_pipeline_does_not_load_whisper_fallback(monkeypatch):
    class Primary:
        def transcribe(self, *args, **kwargs):
            return [ASRCandidate("明天下午三点组会", 0.9, "sensevoice")]

    monkeypatch.setattr("src.voice_understanding.pipeline.create_asr_adapter", lambda settings: Primary())
    monkeypatch.setattr(
        WhisperASRAdapter,
        "transcribe",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("whisper must stay disabled")),
    )

    result = transcribe_audio(
        "unused.wav",
        config=VoiceConfig(enable_trace=False, enable_asr_diagnostics=False),
        adapter=Primary(),
    )

    assert result["mode"] == "sensevoice"
    assert result["fallback_asr_text"] == ""


def test_ffmpeg_missing_does_not_disable_torchaudio_diagnostic(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda command: None)

    result = transcribe_audio(
        "unused.wav",
        adapter=MockASRAdapter([ASRCandidate("明天下午三点组会", 0.9, "mock")]),
        config=VoiceConfig(enable_trace=False, enable_asr_diagnostics=False),
    )

    diagnostic = result["asr_diagnostics"][0]
    assert diagnostic["ffmpeg_available"] is False
    assert diagnostic["torchaudio_available"] is True


def test_cleaned_sensevoice_text_continues_into_semantic_pipeline():
    result = transcribe_audio(
        "unused.wav",
        adapter=MockASRAdapter([
            ASRCandidate(
                "明天下午三点开组会",
                0.9,
                "sensevoice",
                "<|zh|><|NEUTRAL|><|Speech|>明天下午三点开组会",
                ("zh", "NEUTRAL", "Speech"),
            )
        ]),
        config=VoiceConfig(enable_trace=False, enable_asr_diagnostics=False),
    )

    assert result["raw_text"].startswith("<|zh|>")
    assert result["cleaned_text"] == "明天下午三点开组会"
    assert result["semantic_frame"]["intent"] == "add_event"
