import json
from pathlib import Path
from typing import Dict, List, Optional

from src.actions import ActionIntent, validate_action_intent


def load_decision_entries(path: Path) -> List[Dict[str, object]]:
    entries = []
    if not path.exists():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except Exception:
            continue
    return entries


def latest_payload(path: Path) -> Optional[Dict[str, object]]:
    entries = load_decision_entries(path)
    if not entries:
        return None
    return entries[-1].get("payload")


def load_decision_file(path: Path) -> Optional[Dict[str, object]]:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def build_action_intents(payload: Dict[str, object]) -> List[ActionIntent]:
    intents: List[ActionIntent] = []
    actions = payload.get("actions", [])
    if not isinstance(actions, list):
        return intents
    for action in actions:
        if not isinstance(action, dict):
            continue
        intent = ActionIntent(
            intent_id=str(action.get("action_id", "action")),
            action_type=str(action.get("action_type", "")),
            target=action.get("target", {}) if isinstance(action.get("target"), dict) else {},
            confidence=float(action.get("confidence", 1.0)),
            required_cues=action.get("required_cues", []) if isinstance(action.get("required_cues"), list) else [],
            gating=action.get("gating", {}) if isinstance(action.get("gating"), dict) else {},
            payload=action.get("payload", {}) if isinstance(action.get("payload"), dict) else {},
        )
        intents.append(intent)
    return intents


def validate_intents(intents: List[ActionIntent]) -> List[str]:
    errors: List[str] = []
    for idx, intent in enumerate(intents):
        for err in validate_action_intent(intent):
            errors.append(f"intent[{idx}]: {err}")
    return errors


def resolve_target_point(target: Dict[str, object]) -> Optional[tuple]:
    if "x" in target and "y" in target:
        return int(target["x"]), int(target["y"])
    if "position" in target and isinstance(target["position"], (list, tuple)) and len(target["position"]) == 2:
        return int(target["position"][0]), int(target["position"][1])
    if "ui_element_id" in target:
        return None
    return None
