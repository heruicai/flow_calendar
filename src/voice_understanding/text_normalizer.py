"""Low-risk text normalization only."""

from __future__ import annotations

import re
import unicodedata

from src.voice_adapter import normalize_chinese_text


FILLERS = ("\u55ef", "\u5443", "\u90a3\u4e2a", "\u5c31\u662f", "\u8bf7\u5e2e\u6211", "\u5e2e\u6211")


def normalize_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", normalize_chinese_text(str(text or ""))).strip()
    value = re.sub(r"\s+", "", value)
    for filler in FILLERS:
        value = value.replace(filler, "")
    return value.strip(",.!?\uff0c\u3002\uff01\uff1f ")
