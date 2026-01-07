from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from src.timing import sample_gaussian


@dataclass(frozen=True)
class ScrollProfile:
    ticks: Tuple[float, float, float, float] = (3, 1, 1, 6)
    pause_ms: Tuple[float, float, float, float] = (120, 40, 40, 300)


def sample_scroll_ticks(profile: ScrollProfile) -> int:
    mean, stdev, min_val, max_val = profile.ticks
    value = sample_gaussian(mean, stdev, (min_val, max_val))
    return int(round(value))


def sample_scroll_pause_ms(profile: ScrollProfile) -> float:
    mean, stdev, min_val, max_val = profile.pause_ms
    return sample_gaussian(mean, stdev, (min_val, max_val))
