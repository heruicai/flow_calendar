"""Local speech input and output adapters for FlowCal."""

from __future__ import annotations

import os
import re
import tempfile
import time
from pathlib import Path
from uuid import uuid4


DEFAULT_WHISPER_MODEL = "base"
OUTPUT_AUDIO_DIR = Path("outputs/audio")
_WHISPER_MODELS: dict[str, object] = {}


def normalize_voice_text(text: str) -> str:
    """Normalize ASR output before command parsing."""
    normalized = str(text or "").strip()
    normalized = re.sub(r"\s+", "", normalized)
    normalized = normalized.replace(",", "，")
    normalized = normalized.replace("。", "").replace(".", "")
    normalized = normalized.replace("？", "?").replace("！", "!")

    for filler in ("嗯", "呃", "额", "那个", "就是", "请帮我", "帮我"):
        normalized = normalized.replace(filler, "")

    return normalized.strip("，。？！?! ")


def speech_to_text(audio_file=None) -> dict:
    """Transcribe a Streamlit microphone recording locally with faster-whisper."""
    if audio_file is None:
        return _asr_error("没有收到录音，请点击麦克风按钮后再试。")

    temp_path: Path | None = None
    try:
        audio_path, temp_path = _materialize_audio_file(audio_file)
        model_name = os.getenv("FLOWCAL_WHISPER_MODEL", DEFAULT_WHISPER_MODEL)
        model = _get_whisper_model(model_name)
        segments, _ = model.transcribe(
            str(audio_path),
            language="zh",
            vad_filter=True,
            beam_size=5,
        )
        text = normalize_voice_text("".join(segment.text for segment in segments))
        if not text:
            return _asr_error("没有识别到清晰语音，请重新录音。", mode="whisper")
        return {
            "success": True,
            "text": text,
            "message": "已在本机完成语音识别。",
            "mode": "whisper",
        }
    except Exception as exc:  # pragma: no cover - depends on local audio runtime
        return _asr_error(f"本地语音识别失败：{exc}")
    finally:
        if temp_path:
            temp_path.unlink(missing_ok=True)


def text_to_speech(response_text: str) -> dict:
    """Generate a local WAV voice reply with pyttsx3."""
    spoken_text = build_spoken_response(response_text)
    if not spoken_text:
        return _tts_error("没有可朗读的内容。", spoken_text)

    audio_path = OUTPUT_AUDIO_DIR / f"flowcal-{uuid4().hex}.wav"
    try:
        OUTPUT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        pyttsx3 = _load_pyttsx3()
        engine = pyttsx3.init()
        engine.save_to_file(spoken_text, str(audio_path.resolve()))
        engine.runAndWait()
        engine.stop()
        _wait_for_audio_file(audio_path)
        return {
            "success": True,
            "audio_path": str(audio_path),
            "message": "已在本机生成语音回复。",
            "mode": "pyttsx3",
            "spoken_text": spoken_text,
        }
    except Exception as exc:  # pragma: no cover - depends on local TTS runtime
        audio_path.unlink(missing_ok=True)
        return _tts_error(f"本地语音输出失败：{exc}", spoken_text)


def build_spoken_response(response_text: str) -> str:
    """Convert a system response into a concise voice-friendly sentence."""
    spoken_text = str(response_text or "").strip()
    spoken_text = re.sub(r"<[^>]+>", " ", spoken_text)
    spoken_text = re.sub(r"[#>*_`~\[\]()]|^-+\s*", " ", spoken_text)
    spoken_text = re.sub(r"\s+", " ", spoken_text).strip()

    if not spoken_text:
        return ""

    max_length = 140
    if len(spoken_text) > max_length:
        spoken_text = spoken_text[: max_length - 3].rstrip() + "..."
    return spoken_text


def get_voice_input_mode_description() -> str:
    """Return the privacy-oriented voice runtime description."""
    return (
        "麦克风录音通过 st.audio_input 获取，faster-whisper 在本机转写，"
        "pyttsx3 在本机生成语音回复。录音不会上传到外部服务。"
    )


def _materialize_audio_file(audio_file) -> tuple[Path, Path | None]:
    if isinstance(audio_file, (str, os.PathLike)):
        audio_path = Path(audio_file)
        if not audio_path.exists():
            raise FileNotFoundError(f"找不到录音文件：{audio_path}")
        return audio_path, None

    if hasattr(audio_file, "getvalue"):
        audio_bytes = audio_file.getvalue()
    elif hasattr(audio_file, "read"):
        audio_bytes = audio_file.read()
    else:
        raise TypeError("录音对象必须是文件路径或可读取的音频文件。")

    if not audio_bytes:
        raise ValueError("录音内容为空。")

    suffix = Path(getattr(audio_file, "name", "recording.wav")).suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(audio_bytes)
        return Path(temp_file.name), Path(temp_file.name)


def _get_whisper_model(model_name: str):
    if model_name not in _WHISPER_MODELS:
        from faster_whisper import WhisperModel

        _WHISPER_MODELS[model_name] = WhisperModel(
            model_name,
            device="cpu",
            compute_type="int8",
        )
    return _WHISPER_MODELS[model_name]


def _load_pyttsx3():
    import pyttsx3

    return pyttsx3


def _wait_for_audio_file(audio_path: Path) -> None:
    for _ in range(20):
        if audio_path.exists() and audio_path.stat().st_size > 44:
            return
        time.sleep(0.1)
    raise RuntimeError("语音文件没有成功写入。")


def _asr_error(message: str, mode: str = "fallback") -> dict:
    return {
        "success": False,
        "text": "",
        "message": message,
        "mode": mode,
    }


def _tts_error(message: str, spoken_text: str) -> dict:
    return {
        "success": False,
        "audio_path": "",
        "message": message,
        "mode": "fallback",
        "spoken_text": spoken_text,
    }
