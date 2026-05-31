"""Opt-in local regression runner for real voice samples."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.voice_pipeline import transcribe_audio


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default=str(ROOT / "examples" / "voice_samples" / "manifest.json"),
    )
    parser.add_argument(
        "--run-local-asr",
        action="store_true",
        help="Run installed local models. This is opt-in to avoid accidental model downloads.",
    )
    args = parser.parse_args()
    manifest_path = Path(args.manifest)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    samples = payload.get("samples", [])
    if not args.run_local_asr:
        print(json.dumps({"manifest": str(manifest_path), "samples": len(samples), "mode": "validate-only"}, ensure_ascii=False))
        return 0
    failures = 0
    for sample in samples:
        audio_path = manifest_path.parent / sample["file"]
        result = transcribe_audio(audio_path)
        frame = result.get("semantic_frame") or {}
        passed = (
            result.get("text") == sample.get("expected_text")
            and frame.get("intent") == sample.get("expected_intent")
        )
        failures += int(not passed)
        print(json.dumps({
            "file": sample["file"],
            "raw_text": result.get("raw_text", ""),
            "corrected_text": result.get("corrected_text", ""),
            "semantic_frame": frame,
            "passed": passed,
        }, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
