"""Voice interaction adapter for FlowCal.

The current implementation is intentionally stable and local-first: typed text
can simulate speech-to-text output, while real ASR/TTS integrations can be
plugged into the same interface later.
"""

from __future__ import annotations

import re


MOCK_ASR_MESSAGE = "Current version uses text input to simulate speech recognition."
MOCK_TTS_MESSAGE = "Current version uses a mock voice reply and does not generate audio."


def normalize_voice_text(text: str) -> str:
    """Normalize simulated speech-to-text output before command parsing."""
    normalized = text.strip()
    normalized = re.sub(r"\s+", "", normalized)
    normalized = normalized.replace(",", "，")
    normalized = normalized.replace("。", "").replace(".", "")
    normalized = normalized.replace("？", "?").replace("！", "!")

    for filler in ("嗯", "呃", "额", "那个", "就是", "请帮我", "帮我"):
        normalized = normalized.replace(filler, "")

    return normalized.strip("，。!? ")


def speech_to_text(audio_file=None) -> str:
    """Reserved ASR interface.

    Real microphone or audio-file recognition can be added later. Returning an
    empty string keeps the main FlowCal workflow independent from ASR stability.
    """
    return ""


def get_voice_input_mode_description() -> str:
    """Return a short description of the current voice input mode."""
    return (
        "Current version supports text input as simulated speech-to-text. "
        "Future versions can connect Whisper or browser speech recognition."
    )


def build_spoken_response(response_text: str) -> str:
    """Convert system response text into a concise voice-friendly sentence."""
    spoken_text = response_text.strip()
    spoken_text = re.sub(r"<[^>]+>", " ", spoken_text)
    spoken_text = re.sub(r"[#>*_`~\[\]()]|^-+\s*", " ", spoken_text)
    spoken_text = re.sub(r"\s+", " ", spoken_text).strip()

    if not spoken_text:
        return "No response to speak yet."

    max_length = 140
    if len(spoken_text) > max_length:
        spoken_text = spoken_text[: max_length - 3].rstrip() + "..."

    return spoken_text


def text_to_speech(response_text: str) -> dict:
    """Mock TTS adapter that returns structured voice-reply metadata."""
    spoken_text = build_spoken_response(response_text)
    return {
        "success": True,
        "mode": "mock",
        "message": MOCK_TTS_MESSAGE,
        "spoken_text": spoken_text,
    }


def simulate_speech_to_text(text: str) -> str:
    """Return normalized typed text as simulated ASR output."""
    return normalize_voice_text(text)
