from __future__ import annotations

from typing import Any, Dict, Tuple


def _split_hint(text: str) -> Tuple[str, str]:
    cleaned = " ".join(text.split())
    if "-" in cleaned:
        parts = [part.strip() for part in cleaned.split("-", 1)]
        return parts[0], parts[1] if len(parts) > 1 else ""
    if ":" in cleaned:
        parts = [part.strip() for part in cleaned.split(":", 1)]
        return parts[0], parts[1] if len(parts) > 1 else ""
    return cleaned, ""


def infer_region(minimap_region: Any) -> Dict[str, Any]:
    result: Dict[str, Any] = {"region": "unknown", "subarea": "", "confidence": 0.0}
    if not isinstance(minimap_region, dict):
        return result
    region = minimap_region.get("region")
    subarea = minimap_region.get("subarea", "")
    confidence = minimap_region.get("confidence")
    coordinates = minimap_region.get("coordinates") or minimap_region.get("coords")
    hint = None
    for key in ("hint", "label", "name", "text"):
        value = minimap_region.get(key)
        if isinstance(value, str) and value.strip():
            hint = value.strip()
            break
    if hint:
        hint_region, hint_subarea = _split_hint(hint.splitlines()[0])
        if not region:
            region = hint_region
        if not subarea:
            subarea = hint_subarea
        if confidence is None:
            confidence = 0.35
    if region:
        result["region"] = str(region)
        if confidence is None:
            confidence = 0.6
    if subarea:
        result["subarea"] = str(subarea)
    if isinstance(confidence, (int, float)):
        result["confidence"] = float(confidence)
    if isinstance(coordinates, dict):
        result["coordinates"] = coordinates
    elif isinstance(coordinates, (list, tuple)) and len(coordinates) >= 2:
        result["coordinates"] = {"x": coordinates[0], "y": coordinates[1]}
    return result
