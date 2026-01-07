from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from src.timing import sample_gaussian


@dataclass(frozen=True)
class InputNoiseProfile:
    polling_jitter_ms: Tuple[float, float, float, float] = (1.2, 0.6, 0.2, 4.0)
    frame_time_variance_ms: Tuple[float, float, float, float] = (2.0, 0.8, 0.5, 6.0)


def sample_polling_jitter_ms(profile: InputNoiseProfile) -> float:
    mean, stdev, min_val, max_val = profile.polling_jitter_ms
    return sample_gaussian(mean, stdev, (min_val, max_val))


def sample_frame_time_variance_ms(profile: InputNoiseProfile) -> float:
    mean, stdev, min_val, max_val = profile.frame_time_variance_ms
    return sample_gaussian(mean, stdev, (min_val, max_val))
