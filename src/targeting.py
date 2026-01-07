from __future__ import annotations

import random
from typing import Tuple


def choose_target_with_misclick(
    target: Tuple[int, int],
    misclick_rate: float = 0.02,
    max_offset_px: int = 6,
) -> Tuple[Tuple[int, int], bool]:
    if misclick_rate <= 0:
        return target, False
    if random.random() >= misclick_rate:
        return target, False

    dx = random.randint(-max_offset_px, max_offset_px)
    dy = random.randint(-max_offset_px, max_offset_px)
    return (target[0] + dx, target[1] + dy), True


def correction_target(original: Tuple[int, int], misclicked: bool) -> Tuple[int, int]:
    return original if misclicked else original


def avoid_edges(point: Tuple[int, int], bounds: Dict[str, int], margin_px: int = 8) -> Tuple[int, int]:
    x, y = point
    left = bounds.get("x", 0) + margin_px
    top = bounds.get("y", 0) + margin_px
    right = bounds.get("x", 0) + bounds.get("width", 0) - margin_px
    bottom = bounds.get("y", 0) + bounds.get("height", 0) - margin_px

    x = max(left, min(right, x))
    y = max(top, min(bottom, y))
    return x, y
