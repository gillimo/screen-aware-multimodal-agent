"""Fuzzy text matching against known game text references."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MatchResult:
    matched_text: str
    confidence: float
    phase: str
    category: str


def _similarity(a: str, b: str) -> float:
    """Simple similarity score based on common words."""
    if not a or not b:
        return 0.0
    a_lower = a.lower()
    b_lower = b.lower()
    if a_lower == b_lower:
        return 1.0
    if a_lower in b_lower or b_lower in a_lower:
        return 0.8
    a_words = set(a_lower.split())
    b_words = set(b_lower.split())
    if not a_words or not b_words:
        return 0.0
    common = a_words & b_words
    return len(common) / max(len(a_words), len(b_words))


def load_reference(path: Path) -> Dict[str, Any]:
    """Load text reference from JSON file."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def match_text(
    ocr_text: str,
    reference: Dict[str, Any],
    threshold: float = 0.3,
) -> Optional[MatchResult]:
    """Match OCR text against reference, return best match above threshold."""
    if not ocr_text or not reference:
        return None

    best_match: Optional[MatchResult] = None
    best_score = threshold

    phases = reference.get("phases", {})
    for phase_name, phase_data in phases.items():
        if not isinstance(phase_data, dict):
            continue
        for category in ["hints", "npc_dialogue"]:
            texts = phase_data.get(category, [])
            if not isinstance(texts, list):
                continue
            for known_text in texts:
                score = _similarity(ocr_text, known_text)
                if score > best_score:
                    best_score = score
                    best_match = MatchResult(
                        matched_text=known_text,
                        confidence=score,
                        phase=phase_name,
                        category=category,
                    )

    # Also check common buttons
    for button in reference.get("common_buttons", []):
        score = _similarity(ocr_text, button)
        if score > best_score:
            best_score = score
            best_match = MatchResult(
                matched_text=button,
                confidence=score,
                phase="common",
                category="button",
            )

    return best_match


def match_tutorial_hint(ocr_text: str, data_dir: Path) -> Optional[MatchResult]:
    """Convenience function to match against tutorial reference."""
    ref_path = data_dir / "tutorial_text_reference.json"
    reference = load_reference(ref_path)
    return match_text(ocr_text, reference)
