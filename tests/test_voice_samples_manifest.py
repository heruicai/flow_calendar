import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_voice_samples_manifest_exists_and_validate_mode_does_not_load_models():
    manifest = ROOT / "examples" / "voice_samples" / "manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))

    assert isinstance(payload["samples"], list)
    completed = subprocess.run(
        [sys.executable, "scripts/voice_samples_regression.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert '"mode": "validate-only"' in completed.stdout
