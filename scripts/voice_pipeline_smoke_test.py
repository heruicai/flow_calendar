"""Small local smoke test for the text side of the voice pipeline."""

from __future__ import annotations

import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.asr_postprocessor import postprocess_asr_text
from src.glm_semantic_parser import parse_user_command


def main() -> None:
    context = ["算法面试", "组会", "截止时间", "kernelPCA"]
    result = postprocess_asr_text(
        "提醒我明天下午三点蒜粉面试",
        context_terms=context,
        known_task_titles=["算法面试"],
    )
    parsed = parse_user_command(result["corrected_text"], use_ai=False)
    output = {
        "raw_text": result["raw_text"],
        "corrected_text": result["corrected_text"],
        "corrections": result["corrections"],
        "intent": parsed["intent"],
        "title": (parsed.get("task") or {}).get("title"),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    assert result["corrected_text"] == "提醒我明天下午三点算法面试"
    assert parsed["intent"] == "add_event"
    assert (parsed.get("task") or {}).get("title") == "算法面试"


if __name__ == "__main__":
    main()
