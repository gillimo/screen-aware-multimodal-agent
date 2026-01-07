from __future__ import annotations

from typing import Any, Dict


def infer_region(minimap_region: Any) -> Dict[str, Any]:
    if isinstance(minimap_region, dict) and "hint" in minimap_region:
        return {"region": minimap_region.get("hint", "unknown"), "subarea": "", "confidence": 0.2}
    return {"region": "unknown", "subarea": "", "confidence": 0.0}
