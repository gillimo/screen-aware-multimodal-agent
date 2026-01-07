import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CONFIG_PATH = DATA_DIR / "local_model.json"

LAST_REQUEST_AT = 0.0
MIN_INTERVAL_S = 2.0


def load_config():
    if not CONFIG_PATH.exists():
        return {
            "provider": "ollama",
            "host": "http://localhost:11434",
            "model": "phi3:mini",
            "timeout_s": 20,
            "temperature": 0.2,
            "plan_default": "heuristic",
            "strict_json": False,
        }
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {
            "provider": "ollama",
            "host": "http://localhost:11434",
            "model": "phi3:mini",
            "timeout_s": 20,
            "temperature": 0.2,
            "plan_default": "heuristic",
            "strict_json": False,
        }


def build_prompt(state, user_message):
    account = state.get("account", {})
    name = account.get("name", "Unknown")
    return f"You are an OSRS coach. Account: {name}. User says: {user_message}"


def build_decision_prompt(state, user_message):
    account = state.get("account", {})
    name = account.get("name", "Unknown")
    goals = state.get("goals", {})
    short = ", ".join(goals.get("short", []))
    mid = ", ".join(goals.get("mid", []))
    long = ", ".join(goals.get("long", []))
    return (
        "Return ONLY valid JSON for the model output schema.\n"
        f"Account: {name}\n"
        f"Goals short: {short}\n"
        f"Goals mid: {mid}\n"
        f"Goals long: {long}\n"
        f"User: {user_message}\n"
        "Respond with a single JSON object and no extra text."
    )


def _call_ollama(prompt, cfg):
    host = cfg.get("host", "http://localhost:11434").rstrip("/")
    model = cfg.get("model", "phi3:mini")
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": cfg.get("temperature", 0.2),
        },
    }
    req = urllib.request.Request(
        f"{host}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timeout = cfg.get("timeout_s", 20)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("response", "").strip()


def run_local_model(prompt, timeout_s=None):
    global LAST_REQUEST_AT
    now = time.time()
    if now - LAST_REQUEST_AT < MIN_INTERVAL_S:
        return "Rate limit: wait a moment before asking again."
    LAST_REQUEST_AT = now

    cfg = load_config()
    if timeout_s is not None:
        cfg = dict(cfg)
        cfg["timeout_s"] = timeout_s

    provider = cfg.get("provider", "ollama")
    if provider != "ollama":
        return f"Unsupported provider: {provider}"

    try:
        return _call_ollama(prompt, cfg)
    except Exception as exc:
        return f"Local model error: {exc}"
