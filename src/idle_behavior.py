from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class IdleBehaviorProfile:
    idle_rate: float = 0.2
    hover_weight: float = 0.4
    camera_glance_weight: float = 0.2
    inventory_check_weight: float = 0.4
    edge_pause_ms: Tuple[int, int] = (400, 1200)


def should_idle_action(profile: IdleBehaviorProfile) -> bool:
    return random.random() < profile.idle_rate


def choose_idle_action(profile: IdleBehaviorProfile) -> str:
    weights = [
        ("hover", profile.hover_weight),
        ("camera_glance", profile.camera_glance_weight),
        ("inventory_check", profile.inventory_check_weight),
    ]
    total = sum(w for _name, w in weights)
    if total <= 0:
        return "hover"
    pick = random.random() * total
    acc = 0.0
    for name, weight in weights:
        acc += weight
        if pick <= acc:
            return name
    return weights[-1][0]


def screen_edge_pause(bounds: Dict[str, int], margin_px: int = 6) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    x = bounds.get("x", 0)
    y = bounds.get("y", 0)
    width = max(1, bounds.get("width", 1))
    height = max(1, bounds.get("height", 1))
    edge = random.choice(["left", "right", "top", "bottom"])
    if edge == "left":
        leave = (x - margin_px, y + height // 2)
    elif edge == "right":
        leave = (x + width + margin_px, y + height // 2)
    elif edge == "top":
        leave = (x + width // 2, y - margin_px)
    else:
        leave = (x + width // 2, y + height + margin_px)
    return_point = (x + width // 2, y + height // 2)
    return leave, return_point


def idle_recovery_sequence() -> List[str]:
    return ["focus_recovery", "ui_scan", "tab_inventory"]


def choose_tab_toggle(tabs: List[str]) -> str:
    return random.choice(tabs) if tabs else "inventory"
