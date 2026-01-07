import json
from datetime import datetime
from pathlib import Path


def score_from_traces(traces):
    total_events = len(traces)
    action_types = []
    reaction_times = []
    for entry in traces:
        if isinstance(entry, dict):
            action = entry.get("action_type") or entry.get("type")
            if action:
                action_types.append(action)
            rt = entry.get("reaction_ms")
            if isinstance(rt, (int, float)):
                reaction_times.append(rt)
    unique_actions = len(set(action_types))
    reaction_avg = sum(reaction_times) / len(reaction_times) if reaction_times else 0
    return {
        "total_events": total_events,
        "unique_action_types": unique_actions,
        "reaction_ms_avg": round(reaction_avg, 2),
        "notes": "stub scorer; replace with calibrated metrics",
    }


def write_kpi(traces, path):
    result = score_from_traces(traces)
    Path(path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def validate_kpi_schema(kpi):
    errors = []
    required = ["total_events", "unique_action_types", "reaction_ms_avg", "notes"]
    for key in required:
        if key not in kpi:
            errors.append(f"missing {key}")
    return errors


def append_kpi_log(kpi, path):
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "kpi": kpi,
    }
    with Path(path).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry))
        handle.write("\n")
    return entry
