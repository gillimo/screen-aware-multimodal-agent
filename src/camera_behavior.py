from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class CameraProfile:
    nudge_deg: float = 4.0
    overrotate_deg: float = 2.0
    zoom_step: int = 1
    zoom_pause_ms: int = 200


def sample_camera_nudge(profile: CameraProfile) -> float:
    return random.uniform(-profile.nudge_deg, profile.nudge_deg)


def sample_camera_overrotation(profile: CameraProfile) -> float:
    return random.uniform(-profile.overrotate_deg, profile.overrotate_deg)


def sample_zoom_step(profile: CameraProfile) -> int:
    return random.choice([-profile.zoom_step, profile.zoom_step])


def sample_zoom_pause_ms(profile: CameraProfile) -> int:
    return int(random.uniform(profile.zoom_pause_ms * 0.6, profile.zoom_pause_ms * 1.4))


def sample_camera_move(profile: CameraProfile) -> float:
    return sample_camera_nudge(profile) + sample_camera_overrotation(profile)


def choose_rotation_direction(preferred: str = "left") -> int:
    if preferred == "left":
        return -1
    if preferred == "right":
        return 1
    return -1 if random.random() < 0.5 else 1


def apply_camera_drag_slip(delta: float, slip_deg: float = 0.8) -> float:
    return delta + random.uniform(-slip_deg, slip_deg)
