from __future__ import annotations

import math
import random
from typing import List, Tuple


def _ease(t: float, mode: str) -> float:
    if mode == "ease_in":
        return t * t
    if mode == "ease_out":
        return t * (2 - t)
    if mode == "ease_in_out":
        return 0.5 * (math.sin((t - 0.5) * math.pi) + 1)
    return t


def generate_path(
    start: Tuple[float, float],
    end: Tuple[float, float],
    steps: int = 20,
    curve_strength: float = 0.15,
    easing: str = "ease_in_out",
) -> List[Tuple[float, float]]:
    if steps < 2:
        return [start, end]

    sx, sy = start
    ex, ey = end
    mx, my = (sx + ex) / 2, (sy + ey) / 2
    dx, dy = ex - sx, ey - sy
    length = max(1.0, math.hypot(dx, dy))
    nx, ny = -dy / length, dx / length
    control = (mx + nx * length * curve_strength, my + ny * length * curve_strength)

    path: List[Tuple[float, float]] = []
    for i in range(steps):
        t = i / (steps - 1)
        t = _ease(t, easing)
        x = (1 - t) ** 2 * sx + 2 * (1 - t) * t * control[0] + t ** 2 * ex
        y = (1 - t) ** 2 * sy + 2 * (1 - t) * t * control[1] + t ** 2 * ey
        path.append((x, y))
    return path


def generate_speed_ramp(steps: int, mode: str = "ease_in_out") -> List[float]:
    if steps <= 1:
        return [1.0]
    ramp: List[float] = []
    for i in range(steps):
        t = i / (steps - 1)
        ramp.append(_ease(t, mode))
    return ramp


def jitter_start_point(start: Tuple[float, float], radius_px: float = 3.0) -> Tuple[float, float]:
    if radius_px <= 0:
        return start
    sx, sy = start
    dx = random.uniform(-radius_px, radius_px)
    dy = random.uniform(-radius_px, radius_px)
    return sx + dx, sy + dy


def add_tremor(path: List[Tuple[float, float]], amplitude_px: float = 0.4) -> List[Tuple[float, float]]:
    if amplitude_px <= 0:
        return path
    jittered = []
    for x, y in path:
        jittered.append((x + random.uniform(-amplitude_px, amplitude_px), y + random.uniform(-amplitude_px, amplitude_px)))
    return jittered


def generate_drag_path(
    start: Tuple[float, float],
    end: Tuple[float, float],
    steps: int = 20,
    curve_strength: float = 0.15,
    easing: str = "ease_in_out",
    start_jitter_px: float = 2.0,
    end_jitter_px: float = 2.0,
) -> List[Tuple[float, float]]:
    path = generate_path(start, end, steps=steps, curve_strength=curve_strength, easing=easing)
    if not path:
        return path
    if start_jitter_px:
        sx, sy = path[0]
        path[0] = (sx + start_jitter_px, sy + start_jitter_px)
    if end_jitter_px:
        ex, ey = path[-1]
        path[-1] = (ex + end_jitter_px, ey + end_jitter_px)
    return path
