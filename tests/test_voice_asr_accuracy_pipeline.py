import wave

from src.asr_adapter import ASRCandidate, MockASRAdapter
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
        "engine", "model", "language", "beam_size", "vad_enabled",
        "initial_prompt_injected", "audio_duration", "raw_asr_text", "fallback_asr_text",
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
