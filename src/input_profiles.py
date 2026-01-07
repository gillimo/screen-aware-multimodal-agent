from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from src.hardware import InputDevice


@dataclass(frozen=True)
class DeviceProfile:
    device_id: str
    device_type: str
    dpi: Optional[int] = None
    polling_hz: Optional[int] = None
    accel_profile: str = "unknown"


def default_profile(device: InputDevice) -> DeviceProfile:
    return DeviceProfile(device_id=device.device_id, device_type=device.device_type)


def apply_overrides(profile: DeviceProfile, overrides: Dict[str, int]) -> DeviceProfile:
    return DeviceProfile(
        device_id=profile.device_id,
        device_type=profile.device_type,
        dpi=overrides.get("dpi", profile.dpi),
        polling_hz=overrides.get("polling_hz", profile.polling_hz),
        accel_profile=overrides.get("accel_profile", profile.accel_profile),
    )


def build_profiles(
    devices: List[InputDevice],
    overrides_by_id: Optional[Dict[str, Dict[str, int]]] = None,
) -> List[DeviceProfile]:
    profiles: List[DeviceProfile] = []
    overrides_by_id = overrides_by_id or {}
    for device in devices:
        profile = default_profile(device)
        overrides = overrides_by_id.get(device.device_id, {})
        profile = apply_overrides(profile, overrides)
        profiles.append(profile)
    return profiles
