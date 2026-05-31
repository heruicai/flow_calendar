"""Privacy-conscious local JSONL traces."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from src.voice_understanding.schema import VoiceUnderstandingResult


def write_trace(result: VoiceUnderstandingResult, trace_dir="outputs/voice_traces") -> Path:
    directory = Path(trace_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{datetime.now():%Y%m%d}.jsonl"
    payload = result.to_dict()
    payload["created_at"] = datetime.now().isoformat(timespec="seconds")
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path
