from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol


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


class TesseractOcrProvider:
    def __init__(self, tesseract_cmd: str = "") -> None:
        self.tesseract_cmd = tesseract_cmd

    def read(self, regions: Dict[str, Any]) -> List[OcrEntry]:
        try:
            import pytesseract
            from PIL import Image
        except Exception:
            return []

        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

        entries: List[OcrEntry] = []
        for name, bounds in regions.items():
            if not isinstance(bounds, dict):
                continue
            width = int(bounds.get("width", 0) or 0)
            height = int(bounds.get("height", 0) or 0)
            if width <= 0 or height <= 0:
                continue
            try:
                image = bounds.get("_image")
                if image is None:
                    continue
                crop = image.crop(
                    (
                        int(bounds.get("x", 0)),
                        int(bounds.get("y", 0)),
                        int(bounds.get("x", 0)) + width,
                        int(bounds.get("y", 0)) + height,
                    )
                )
                text = pytesseract.image_to_string(crop)
                entries.append(OcrEntry(region=name, text=text.strip(), confidence=0.5))
            except Exception:
                continue
        return entries


_PROVIDERS: Dict[str, OcrProvider] = {
    "noop": NoopOcrProvider(),
}


def register_provider(name: str, provider: OcrProvider) -> None:
    _PROVIDERS[name] = provider


def get_provider(name: str) -> OcrProvider:
    return _PROVIDERS.get(name, _PROVIDERS["noop"])


def run_ocr(
    regions: Dict[str, Any],
    provider_name: str = "noop",
    provider_config: Optional[Dict[str, Any]] = None,
) -> List[OcrEntry]:
    if provider_name == "tesseract":
        tesseract_cmd = ""
        if isinstance(provider_config, dict):
            tesseract_cmd = str(provider_config.get("tesseract_cmd", "") or "")
        provider = TesseractOcrProvider(tesseract_cmd=tesseract_cmd)
        return provider.read(regions)
    provider = get_provider(provider_name)
    return provider.read(regions)
