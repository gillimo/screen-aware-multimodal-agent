from __future__ import annotations

import random
from typing import Tuple


def apply_attention_drift(
    point: Tuple[float, float],
    drift_px: float = 0.5,
    bias_x: float = 0.1,
    bias_y: float = -0.1,
) -> Tuple[float, float]:
    x, y = point
    dx = random.uniform(-drift_px, drift_px) + bias_x
    dy = random.uniform(-drift_px, drift_px) + bias_y
    return x + dx, y + dy
