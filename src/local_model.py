import json
import time
import urllib.request
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CONFIG_PATH = DATA_DIR / "local_model.json"
GUIDES_PATH = DATA_DIR / "quest_guides.json"

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
            "strict_json_retries": 2,
            "safety_gates_enabled": False,
            "approval_policy": {
                "require_approval": False,
                "unsafe_actions": ["drag", "type", "camera"],
                "auto_approve_actions": [],
            },
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
            "strict_json_retries": 2,
            "safety_gates_enabled": False,
            "approval_policy": {
                "require_approval": False,
                "unsafe_actions": ["drag", "type", "camera"],
                "auto_approve_actions": [],
            },
        }


def build_prompt(state, user_message):
    account = state.get("account", {})
    name = account.get("name", "Unknown")
    return f"You are an OSRS coach. Account: {name}. User says: {user_message}"


def build_decision_prompt(state, user_message, snapshot=None):
    account = state.get("account", {})
    name = account.get("name", "Unknown")
    goals = state.get("goals", {})
    short = ", ".join(goals.get("short", []))
    mid = ", ".join(goals.get("mid", []))
    long = ", ".join(goals.get("long", []))
    guide_block = _build_quest_guide_context(state, user_message)
    snapshot_block = _build_snapshot_context(snapshot)
    return (
        "Return ONLY valid JSON for the model output schema.\n"
        f"Account: {name}\n"
        f"Goals short: {short}\n"
        f"Goals mid: {mid}\n"
        f"Goals long: {long}\n"
        f"{guide_block}"
        f"{snapshot_block}"
        f"User: {user_message}\n"
        "Respond with a single JSON object and no extra text."
    )


def _build_quest_guide_context(state, user_message: str) -> str:
    try:
        from src.quest_guides import load_guides, retrieve_guides
    except Exception:
        return ""
    guides = load_guides(GUIDES_PATH)
    goals = state.get("goals", {}) if isinstance(state, dict) else {}
    goal_text = " ".join(
        [
            " ".join(goals.get("short", [])),
            " ".join(goals.get("mid", [])),
            " ".join(goals.get("long", [])),
        ]
    )
    query = " ".join([user_message or "", goal_text]).strip()
    matches = retrieve_guides(query, guides, limit=3)
    if not matches:
        return ""
    lines: List[str] = ["Quest guide snippets:"]
    for guide in matches:
        quest = str(guide.get("quest", "")).strip()
        summary = str(guide.get("summary", "")).strip()
        steps = guide.get("steps", []) if isinstance(guide.get("steps"), list) else []
        if quest:
            lines.append(f"- {quest}: {summary}" if summary else f"- {quest}")
        for step in steps[:3]:
            step_text = str(step).strip()
            if step_text:
                lines.append(f"  * {step_text}")
    return "\n".join(lines) + "\n"


def _build_snapshot_context(snapshot) -> str:
    if not isinstance(snapshot, dict):
        return ""
    ui = snapshot.get("ui", {}) if isinstance(snapshot.get("ui"), dict) else {}
    cues = snapshot.get("cues", {}) if isinstance(snapshot.get("cues"), dict) else {}
    chat_lines = snapshot.get("chat", []) if isinstance(snapshot.get("chat"), list) else []
    dialogue = ui.get("dialogue_options", []) if isinstance(ui.get("dialogue_options"), list) else []
    hover_text = ui.get("hover_text", "")
    open_interface = ui.get("open_interface", "")
    selected_tab = ui.get("selected_tab", "")
    chat_prompt = cues.get("chat_prompt", "")
    lines: List[str] = []
    if chat_lines:
        lines.append("Chat lines:")
        lines.extend([f"- {line}" for line in chat_lines[:5]])
    if dialogue:
        lines.append("Dialogue options:")
        lines.extend([f"- {line}" for line in dialogue[:5]])
    if hover_text:
        lines.append(f"Hover text: {hover_text}")
    if chat_prompt:
        lines.append(f"Chat prompt: {chat_prompt}")
    if open_interface or selected_tab:
        lines.append(f"UI: interface={open_interface or 'none'}, tab={selected_tab or 'unknown'}")
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


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
