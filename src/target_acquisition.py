from __future__ import annotations

import random
from typing import Dict, Tuple


def choose_aim_point(bounds: Dict[str, int], bias: str = "center", drift_px: int = 2) -> Tuple[int, int]:
    x = bounds.get("x", 0)
    y = bounds.get("y", 0)
    width = max(1, bounds.get("width", 1))
    height = max(1, bounds.get("height", 1))

    if bias == "text_center":
        base_x = x + int(width * 0.55)
        base_y = y + int(height * 0.5)
    elif bias == "icon_center":
        base_x = x + int(width * 0.45)
        base_y = y + int(height * 0.5)
    else:
        base_x = x + width // 2
        base_y = y + height // 2

    dx = random.randint(-drift_px, drift_px)
    dy = random.randint(-drift_px, drift_px)
    return base_x + dx, base_y + dy


def choose_biased_target(
    bounds: Dict[str, int],
    bias: str = "center",
    drift_px: int = 2,
) -> Tuple[int, int]:
    return choose_aim_point(bounds, bias=bias, drift_px=drift_px)
