from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Iterable


@dataclass(frozen=True)
class InterruptProfile:
    delay_ms: tuple = (180, 60, 80, 420)
    panic_keywords: tuple = ("trade", "duel", "stake", "accept")


def should_pause_on_unexpected_ui(snapshot: Dict[str, object]) -> bool:
    ui = snapshot.get("ui", {}) if isinstance(snapshot, dict) else {}
    cues = snapshot.get("cues", {}) if isinstance(snapshot, dict) else {}
    if ui.get("open_interface") not in {"none", "inventory", "skills"}:
        return True
    if cues.get("modal_state") not in {"none", "", "unknown"}:
        return True
    return False


def sample_interruption_delay_ms(profile: InterruptProfile) -> float:
    mean, stdev, min_val, max_val = profile.delay_ms
    value = random.gauss(mean, stdev)
    return max(min_val, min(max_val, value))


def should_panic_on_chat(lines: Iterable[str], profile: InterruptProfile) -> bool:
    for line in lines:
        lowered = line.lower()
        if any(keyword in lowered for keyword in profile.panic_keywords):
            return True
    return False
