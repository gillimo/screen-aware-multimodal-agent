from __future__ import annotations

from typing import Dict, Optional


def is_occluded(element: Dict[str, str]) -> bool:
    state = str(element.get("state", "")).lower()
    return "occluded" in state or "blocked" in state


def should_wait_for_occlusion(snapshot: Dict[str, object], element_id: str) -> bool:
    ui = snapshot.get("ui", {}) if isinstance(snapshot, dict) else {}
    elements = ui.get("elements", [])
    if not isinstance(elements, list):
        return False
    for element in elements:
        if not isinstance(element, dict):
            continue
        if element.get("id") == element_id and is_occluded(element):
            return True
    return False


def occlusion_reason(snapshot: Dict[str, object], element_id: str) -> Optional[str]:
    ui = snapshot.get("ui", {}) if isinstance(snapshot, dict) else {}
    elements = ui.get("elements", [])
    if not isinstance(elements, list):
        return None
    for element in elements:
        if not isinstance(element, dict):
            continue
        if element.get("id") == element_id and is_occluded(element):
            return element.get("state", "occluded")
    return None
