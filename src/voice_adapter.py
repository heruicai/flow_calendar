"""Voice adapter interfaces.

The first version treats typed text as simulated speech-to-text output.
"""


def simulate_speech_to_text(text: str) -> str:
    """Return typed text as simulated ASR output."""
    return text.strip()
