from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Tuple

from src.timing import sample_gaussian


@dataclass(frozen=True)
class TypingProfile:
    key_delay_ms: Tuple[float, float, float, float] = (85, 30, 30, 180)
    burst_chars: Tuple[float, float, float, float] = (6, 2, 2, 12)
    correction_rate: float = 0.03
    backspace_ms: Tuple[float, float, float, float] = (90, 25, 30, 200)
    overlap_ms: Tuple[float, float, float, float] = (15, 6, 5, 40)
    modifier_rate: float = 0.15


def sample_key_delay_ms(profile: TypingProfile) -> float:
    mean, stdev, min_val, max_val = profile.key_delay_ms
    return sample_gaussian(mean, stdev, (min_val, max_val))


def sample_burst_chars(profile: TypingProfile) -> int:
    mean, stdev, min_val, max_val = profile.burst_chars
    value = sample_gaussian(mean, stdev, (min_val, max_val))
    return int(round(value))


def should_correct_typo(profile: TypingProfile) -> bool:
    return random.random() < profile.correction_rate


def sample_backspace_ms(profile: TypingProfile) -> float:
    mean, stdev, min_val, max_val = profile.backspace_ms
    return sample_gaussian(mean, stdev, (min_val, max_val))


def sample_key_overlap_ms(profile: TypingProfile) -> float:
    mean, stdev, min_val, max_val = profile.overlap_ms
    return sample_gaussian(mean, stdev, (min_val, max_val))


def should_use_modifier(profile: TypingProfile) -> bool:
    return random.random() < profile.modifier_rate
