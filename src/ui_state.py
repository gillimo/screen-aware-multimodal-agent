from __future__ import annotations

from typing import Iterable, Optional

from src.ocr import OcrEntry

KNOWN_CURSOR_STATES = {"default", "interact", "attack", "use", "talk", "walk", "unknown"}


def extract_cursor_state(cursor_hint: Optional[str]) -> str:
    if not cursor_hint:
        return "unknown"
    hint = cursor_hint.strip().lower()
    return hint if hint in KNOWN_CURSOR_STATES else "unknown"


def extract_hover_text(entries: Iterable[OcrEntry], region_name: str = "hover") -> str:
    for entry in entries:
        if entry.region == region_name and entry.text:
            return entry.text
    return ""
