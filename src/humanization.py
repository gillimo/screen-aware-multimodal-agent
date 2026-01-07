import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROFILE_PATH = DATA_DIR / "humanization_profiles.json"
LOCAL_PROFILE_PATH = DATA_DIR / "humanization_profiles.local.json"


def _load_json(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_profiles():
    base = _load_json(PROFILE_PATH)
    overrides = _load_json(LOCAL_PROFILE_PATH)
    profiles = dict(base.get("profiles", {}))
    profiles.update(overrides.get("profiles", {}))
    return {"version": base.get("version", 1), "profiles": profiles}


def list_profiles():
    data = load_profiles()
    return sorted(data.get("profiles", {}).keys())


def get_profile(name):
    data = load_profiles()
    return data.get("profiles", {}).get(name)


def get_active_profile():
    cfg = _load_json(DATA_DIR / "local_model.json")
    name = cfg.get("active_profile")
    if not name:
        return None
    return get_profile(name)
