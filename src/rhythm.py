from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Tuple

from src.timing import sample_gaussian


@dataclass(frozen=True)
class BurstProfile:
    actions_per_burst: Tuple[float, float, float, float] = (6, 2, 2, 12)
    rest_ms: Tuple[float, float, float, float] = (900, 250, 300, 2000)


@dataclass(frozen=True)
class SessionRhythmProfile:
    burst_profile: BurstProfile = BurstProfile()
    fatigue_drift_rate: float = 0.02


def sample_burst_actions(profile: BurstProfile) -> int:
    mean, stdev, min_val, max_val = profile.actions_per_burst
    value = sample_gaussian(mean, stdev, (min_val, max_val))
    return int(round(value))


def sample_rest_ms(profile: BurstProfile) -> float:
    mean, stdev, min_val, max_val = profile.rest_ms
    return sample_gaussian(mean, stdev, (min_val, max_val))


def apply_fatigue_drift(base_ms: float, minutes_elapsed: float, drift_rate: float) -> float:
    if minutes_elapsed <= 0:
        return base_ms
    return base_ms * (1 + drift_rate * minutes_elapsed)


def maybe_take_break(break_chance: float = 0.05) -> bool:
    return random.random() < break_chance
