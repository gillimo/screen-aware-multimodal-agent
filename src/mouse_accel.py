from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class AccelProfile:
    name: str
    exponent: float


_PRESETS: Dict[str, AccelProfile] = {
    "linear": AccelProfile(name="linear", exponent=1.0),
    "windows_default": AccelProfile(name="windows_default", exponent=1.2),
    "low": AccelProfile(name="low", exponent=0.9),
    "high": AccelProfile(name="high", exponent=1.4),
}


def get_profile(name: str) -> AccelProfile:
    return _PRESETS.get(name, _PRESETS["linear"])


def apply_accel(progress: float, profile: AccelProfile) -> float:
    if progress <= 0:
        return 0.0
    if progress >= 1:
        return 1.0
    return progress ** profile.exponent
