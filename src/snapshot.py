from __future__ import annotations

from typing import Any, Dict, List


REQUIRED_TOP_LEVEL = [
    "timestamp",
    "session_id",
    "client",
    "roi",
    "ui",
    "ocr",
    "cues",
    "derived",
    "account",
]

REQUIRED_CLIENT_FIELDS = [
    "window_title",
    "bounds",
    "focused",
    "scale",
    "fps",
    "capture_latency_ms",
]


def validate_snapshot(snapshot: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not isinstance(snapshot, dict):
        return ["snapshot must be a JSON object"]

    for field in REQUIRED_TOP_LEVEL:
        if field not in snapshot:
            errors.append(f"missing {field}")

    client = snapshot.get("client", {})
    if not isinstance(client, dict):
        errors.append("client must be an object")
    else:
        for field in REQUIRED_CLIENT_FIELDS:
            if field not in client:
                errors.append(f"client missing {field}")

    if "roi" in snapshot and not isinstance(snapshot.get("roi"), dict):
        errors.append("roi must be an object")

    if "ui" in snapshot and not isinstance(snapshot.get("ui"), dict):
        errors.append("ui must be an object")

    if "ocr" in snapshot and not isinstance(snapshot.get("ocr"), list):
        errors.append("ocr must be an array")

    if "cues" in snapshot and not isinstance(snapshot.get("cues"), dict):
        errors.append("cues must be an object")

    if "derived" in snapshot and not isinstance(snapshot.get("derived"), dict):
        errors.append("derived must be an object")

    if "account" in snapshot and not isinstance(snapshot.get("account"), dict):
        errors.append("account must be an object")

    return errors
