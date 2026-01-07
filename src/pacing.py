from __future__ import annotations

from typing import Dict


def pacing_multiplier(context: str = "simple") -> float:
    if context == "complex":
        return 1.3
    if context == "idle":
        return 1.1
    return 0.9 if context == "simple" else 1.0


def spacing_from_cues(cues: Dict[str, object], base_ms: float = 200) -> float:
    animation_state = str(cues.get("animation_state", "")).lower()
    if animation_state in {"active", "cooldown"}:
        return base_ms * 1.5
    return base_ms


def adjusted_action_delay(
    base_ms: float,
    cues: Dict[str, object],
    context: str = "default",
) -> float:
    spacing = spacing_from_cues(cues, base_ms=base_ms)
    return spacing * pacing_multiplier(context)
