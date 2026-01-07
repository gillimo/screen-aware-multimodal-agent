from __future__ import annotations

from typing import Dict, List, Tuple


def build_scan_points(bounds: Dict[str, int], steps: int = 5) -> List[Tuple[int, int]]:
    x = bounds.get("x", 0)
    y = bounds.get("y", 0)
    width = max(1, bounds.get("width", 1))
    height = max(1, bounds.get("height", 1))

    points: List[Tuple[int, int]] = []
    for idx in range(steps):
        t = idx / max(1, steps - 1)
        px = x + int(width * t)
        py = y + int(height * (0.5 if idx % 2 == 0 else 0.25))
        points.append((px, py))
    return points
