import json
from pathlib import Path

from src.model_output import validate_planner_output
from src.schema_validation import (
    validate_snapshot_schema,
    validate_agent_state_schema,
    validate_agent_decisions_schema,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def load_json(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def select_decision(phase, decisions, index=0):
    phase_list = decisions.get("phases", {}).get(phase, [])
    if not phase_list:
        return None
    if index < 0 or index >= len(phase_list):
        index = 0
    return phase_list[index]


def cues_met(snapshot, decision) -> bool:
    if not isinstance(decision, dict):
        return True
    required = decision.get("required_cues", [])
    if not required:
        return True
    cues = snapshot.get("cues", {}) if isinstance(snapshot.get("cues"), dict) else {}
    for cue in required:
        if not cues.get(cue):
            return False
    return True


def run_loop(snapshot_path, state_path, decisions_path, out_path=None):
    snapshot = load_json(Path(snapshot_path))
    state = load_json(Path(state_path))
    decisions = load_json(Path(decisions_path))

    snap_errors = validate_snapshot_schema(snapshot)
    if snap_errors:
        raise SystemExit(f"Snapshot schema errors: {snap_errors}")
    state_errors = validate_agent_state_schema(state)
    if state_errors:
        raise SystemExit(f"Agent state schema errors: {state_errors}")
    decisions_errors = validate_agent_decisions_schema(decisions)
    if decisions_errors:
        raise SystemExit(f"Agent decisions schema errors: {decisions_errors}")

    phase = state.get("phase", "welcome")
    phase_list = decisions.get("phases", {}).get(phase, [])
    decision_index = int(state.get("decision_index", 0) or 0)
    repeat_count = int(state.get("repeat_count", 0) or 0)
    stale = bool(snapshot.get("stale", False))
    decision = select_decision(phase, decisions, index=decision_index)
    if decision is not None and repeat_count >= 2 and (stale or not cues_met(snapshot, decision)):
        if phase_list:
            decision_index = (decision_index + 1) % len(phase_list)
            decision = select_decision(phase, decisions, index=decision_index)
            state["decision_index"] = decision_index
            Path(state_path).write_text(json.dumps(state, indent=2), encoding="utf-8")
    if decision is None:
        raise SystemExit(f"No decision template for phase: {phase}")

    errors = validate_planner_output(decision)
    if errors:
        raise SystemExit(f"Decision schema errors: {errors}")

    payload = json.dumps(decision, indent=2)
    if out_path:
        Path(out_path).write_text(payload, encoding="utf-8")
    else:
        print(payload)

    return {
        "phase": phase,
        "decision_id": decision.get("decision_id"),
        "snapshot": snapshot_path,
        "decision": decision,
    }


if __name__ == "__main__":
    default_snapshot = DATA_DIR / "snapshots" / "snapshot_latest.json"
    default_state = DATA_DIR / "agent_state.json"
    default_decisions = DATA_DIR / "agent_decisions.json"
    run_loop(default_snapshot, default_state, default_decisions)
