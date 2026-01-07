from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol


@dataclass(frozen=True)
class UiElement:
    element_id: str
    element_type: str
    label: str
    state: str
    bounds: Dict[str, int]


class UiDetector(Protocol):
    def detect(self, regions: Dict[str, Any]) -> List[UiElement]:
        ...


class NoopUiDetector:
    def detect(self, regions: Dict[str, Any]) -> List[UiElement]:
        return []


_DETECTORS: Dict[str, UiDetector] = {
    "noop": NoopUiDetector(),
}


def register_detector(name: str, detector: UiDetector) -> None:
    _DETECTORS[name] = detector


def get_detector(name: str) -> UiDetector:
    return _DETECTORS.get(name, _DETECTORS["noop"])


def detect_ui(regions: Dict[str, Any], detector_name: str = "noop") -> List[UiElement]:
    detector = get_detector(detector_name)
    return detector.detect(regions)
