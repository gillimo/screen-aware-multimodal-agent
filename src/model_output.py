import json
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)


REQUIRED_FIELDS = [
    "decision_id",
    "intent",
    "confidence",
    "rationale",
    "required_cues",
    "risks",
    "actions",
]

ACTION_FIELDS = [
    "action_id",
    "action_type",
    "target",
    "confidence",
    "gating",
]

TRACE_FIELDS = [
    "timestamp",
    "source",
    "message",
    "payload",
]


def extract_json(text):
    if not isinstance(text, str):
        return None
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except Exception:
            return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except Exception:
        return None


def validate_planner_output(payload):
    errors = []
    if not isinstance(payload, dict):
        return ["payload must be a JSON object"]
    for key in REQUIRED_FIELDS:
        if key not in payload:
            errors.append(f"missing {key}")
    actions = payload.get("actions", [])
    if not isinstance(actions, list):
        errors.append("actions must be an array")
        return errors
    for idx, action in enumerate(actions):
        if not isinstance(action, dict):
            errors.append(f"actions[{idx}] must be an object")
            continue
        for key in ACTION_FIELDS:
            if key not in action:
                errors.append(f"actions[{idx}] missing {key}")
    return errors


def log_decision(payload, source, message, path: Path | None = None):
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": source,
        "message": message,
        "payload": payload,
    }
    if path is None:
        path = LOG_DIR / "model_decisions.jsonl"
    path.parent.mkdir(exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry))
        handle.write("\n")


def validate_decision_trace(entry):
    errors = []
    if not isinstance(entry, dict):
        return ["trace entry must be a JSON object"]
    for key in TRACE_FIELDS:
        if key not in entry:
            errors.append(f"missing {key}")
    payload = entry.get("payload")
    if payload is not None:
        errors.extend(validate_planner_output(payload))
    return errors


def purge_decisions(days):
    path = LOG_DIR / "model_decisions.jsonl"
    if not path.exists():
        return 0
    cutoff = datetime.utcnow() - timedelta(days=days)
    kept = []
    removed = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            ts = entry.get("timestamp", "")
            try:
                stamp = datetime.fromisoformat(ts.replace("Z", ""))
            except Exception:
                kept.append(line)
                continue
            if stamp < cutoff:
                removed += 1
            else:
                kept.append(line)
    with path.open("w", encoding="utf-8") as handle:
        for line in kept:
            handle.write(line)
            handle.write("\n")
    return removed
