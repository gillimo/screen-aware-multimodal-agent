from __future__ import annotations

from typing import Dict, List, Tuple


def offscreen_travel(bounds: Dict[str, int], margin_px: int = 12) -> List[Tuple[int, int]]:
    x = bounds.get("x", 0)
    y = bounds.get("y", 0)
    width = max(1, bounds.get("width", 1))
    height = max(1, bounds.get("height", 1))
    center = (x + width // 2, y + height // 2)
    leave = (x + width + margin_px, y + height + margin_px)
    return [center, leave, center]
