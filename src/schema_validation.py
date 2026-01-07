import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
STATE_SCHEMA_PATH = DATA_DIR / "state_schema.json"
SNAPSHOT_SCHEMA_PATH = DATA_DIR / "snapshot_schema.json"
HUMANIZATION_SCHEMA_PATH = DATA_DIR / "humanization_profiles_schema.json"
DECISION_TRACE_SCHEMA_PATH = DATA_DIR / "decision_trace_schema.json"
HUMAN_KPI_LOG_SCHEMA_PATH = DATA_DIR / "human_kpi_log_schema.json"

TYPE_MAP = {
    "string": str,
    "number": (int, float),
    "object": dict,
    "array": list,
    "boolean": bool,
}


def _load_schema(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _check_type(value, expected):
    expected_type = TYPE_MAP.get(expected)
    if expected_type is None:
        return True
    return isinstance(value, expected_type)


def _validate_object(obj, schema, path, errors):
    if not isinstance(obj, dict):
        errors.append(f"{path.rstrip('.')}: expected object")
        return

    for key in schema.get("required", []):
        if key not in obj:
            errors.append(f"{path}{key}: missing required field")

    for key, type_name in schema.get("types", {}).items():
        if key in obj and not _check_type(obj[key], type_name):
            errors.append(f"{path}{key}: expected {type_name}")

    for key, sub_schema in schema.get("objects", {}).items():
        if key in obj and isinstance(obj[key], dict):
            _validate_object(obj[key], sub_schema, f"{path}{key}.", errors)

    for key, elem_type in schema.get("arrays", {}).items():
        if key in obj:
            val = obj[key]
            if not isinstance(val, list):
                errors.append(f"{path}{key}: expected array")
                continue
            for idx, item in enumerate(val):
                if not _check_type(item, elem_type):
                    errors.append(f"{path}{key}[{idx}]: expected {elem_type}")


def validate_state_schema(state):
    schema = _load_schema(STATE_SCHEMA_PATH)
    if schema is None:
        return []
    errors = []
    _validate_object(state, schema, "", errors)
    return errors


def validate_snapshot_schema(snapshot):
    schema = _load_schema(SNAPSHOT_SCHEMA_PATH)
    if schema is None:
        return []
    errors = []
    _validate_object(snapshot, schema, "", errors)
    return errors


def validate_humanization_schema(profiles):
    schema = _load_schema(HUMANIZATION_SCHEMA_PATH)
    if schema is None:
        return []
    errors = []
    _validate_object(profiles, schema, "", errors)
    return errors


def validate_decision_trace_schema(entry):
    schema = _load_schema(DECISION_TRACE_SCHEMA_PATH)
    if schema is None:
        return []
    errors = []
    _validate_object(entry, schema, "", errors)
    return errors


def validate_human_kpi_log_schema(entry):
    schema = _load_schema(HUMAN_KPI_LOG_SCHEMA_PATH)
    if schema is None:
        return []
    errors = []
    _validate_object(entry, schema, "", errors)
    return errors
