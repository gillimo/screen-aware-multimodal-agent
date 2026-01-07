import re
from pathlib import Path
from typing import Dict, List

from src.engine import load_json


def load_guides(path: Path) -> List[Dict[str, object]]:
    payload = load_json(path, {})
    if not isinstance(payload, dict):
        return []
    guides = payload.get("guides", [])
    return guides if isinstance(guides, list) else []


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def retrieve_guides(query: str, guides: List[Dict[str, object]], limit: int = 3) -> List[Dict[str, object]]:
    if not query or not guides:
        return []
    query_tokens = set(_tokenize(query))
    scored = []
    for guide in guides:
        name = str(guide.get("quest", ""))
        if not name:
            continue
        name_tokens = set(_tokenize(name))
        score = len(query_tokens & name_tokens)
        if score > 0:
            scored.append((score, guide))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [guide for _score, guide in scored[:limit]]
