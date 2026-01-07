from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol


@dataclass(frozen=True)
class OcrEntry:
    region: str
    text: str
    confidence: float


class OcrProvider(Protocol):
    def read(self, regions: Dict[str, Any]) -> List[OcrEntry]:
        ...


class NoopOcrProvider:
    def read(self, regions: Dict[str, Any]) -> List[OcrEntry]:
        return []


_PROVIDERS: Dict[str, OcrProvider] = {
    "noop": NoopOcrProvider(),
}


def register_provider(name: str, provider: OcrProvider) -> None:
    _PROVIDERS[name] = provider


def get_provider(name: str) -> OcrProvider:
    return _PROVIDERS.get(name, _PROVIDERS["noop"])


def run_ocr(regions: Dict[str, Any], provider_name: str = "noop") -> List[OcrEntry]:
    provider = get_provider(provider_name)
    return provider.read(regions)
