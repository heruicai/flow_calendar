"""Small local WAV checks. No audio leaves the machine."""

from __future__ import annotations

import wave
from pathlib import Path

from src.voice_understanding.schema import AudioQuality


def inspect_audio_quality(audio_path, *, threshold: float = 0.35) -> AudioQuality:
    """Check readable WAV metadata when available.

    Non-WAV files remain eligible for local ASR because optional engines can
    decode them. Empty and unreadable files are rejected early.
    """
    path = Path(audio_path)
    if not path.exists() or path.stat().st_size == 0:
        return AudioQuality(0.0, False, "empty_or_missing_audio")
    if path.suffix.lower() not in {".wav", ".wave"}:
        return _inspect_non_wav_audio(path)
    try:
        with wave.open(str(path), "rb") as audio:
            frames = audio.getnframes()
            rate = audio.getframerate()
            channels = audio.getnchannels()
    except (EOFError, wave.Error):
        return AudioQuality(0.0, False, "unreadable_wav")
    duration = frames / rate if rate else 0.0
    score = 1.0
    reason = "ok"
    if duration < 0.2:
        score, reason = 0.15, "audio_too_short"
    elif duration > 120:
        score, reason = 0.3, "audio_too_long"
    elif rate < 8000 or channels not in {1, 2}:
        score, reason = 0.3, "unsupported_audio_layout"
    return AudioQuality(score, score >= threshold, reason, round(duration, 3), rate, channels)


def _inspect_non_wav_audio(path: Path) -> AudioQuality:
    try:
        import soundfile

        info = soundfile.info(str(path))
        duration = float(info.duration)
        return AudioQuality(
            0.7,
            True,
            "decoded_metadata_with_soundfile",
            round(duration, 3),
            int(info.samplerate),
            int(info.channels),
        )
    except Exception:
        return AudioQuality(0.7, True, "decoder_check_deferred_to_local_asr")
