from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACTIONS = ROOT / "logs" / "actions.jsonl"
DEFAULT_CONTEXT = ROOT / "logs" / "action_context.jsonl"
DEFAULT_EXECUTION = ROOT / "logs" / "execution_summary.json"
DEFAULT_OUT = ROOT / "logs" / "mimicry_scores.jsonl"


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except Exception:
            continue
    return entries


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _mean_std(values: List[float]) -> tuple[Optional[float], Optional[float]]:
    if not values:
        return None, None
    if len(values) == 1:
        return values[0], 0.0
    return statistics.mean(values), statistics.pstdev(values)


def _score_timing(timing_entries: List[Dict[str, Any]]) -> tuple[int, Dict[str, Any]]:
    reaction_values = [
        float(t.get("reaction_ms"))
        for t in timing_entries
        if isinstance(t.get("reaction_ms"), (int, float))
    ]
    mean, stdev = _mean_std(reaction_values)
    if not reaction_values:
        return 1, {"reaction_samples": 0}
    cv = stdev / mean if mean and stdev is not None else 0.0
    score = 3
    if 80 <= mean <= 400 and 0.1 <= cv <= 0.6:
        score = 4
    if 80 <= mean <= 350 and 0.15 <= cv <= 0.5 and len(reaction_values) >= 10:
        score = 5
    return score, {"reaction_samples": len(reaction_values), "reaction_mean_ms": mean, "reaction_cv": cv}


def _score_motion(motion_entries: List[Dict[str, Any]]) -> tuple[int, Dict[str, Any]]:
    fields = {"curve_strength", "speed_ramp_mode", "overshoot_px", "start_jitter_px", "edge_margin_px"}
    present = set()
    for motion in motion_entries:
        if not isinstance(motion, dict):
            continue
        for field in fields:
            if field in motion:
                present.add(field)
    score = 1
    if len(present) >= 3:
        score = 3
    if len(present) >= 4:
        score = 4
    if len(present) == len(fields):
        score = 5
    return score, {"motion_fields_present": sorted(present)}


def _score_error(actions: List[Dict[str, Any]]) -> tuple[int, Dict[str, Any]]:
    failures = 0
    total = 0
    misclicks = 0
    for entry in actions:
        result = entry.get("result", {})
        if not isinstance(result, dict):
            continue
        total += 1
        if not result.get("success", True):
            failures += 1
        reason = str(result.get("failure_reason", "")).lower()
        if reason in {"misclick", "near_miss"}:
            misclicks += 1
    rate = failures / total if total else 0.0
    score = 1 if total else 0
    if misclicks > 0 or failures > 0:
        score = 3
    if 0 < rate <= 0.02:
        score = 4
    if 0.02 < rate <= 0.05:
        score = 3
    return score, {"actions": total, "failure_rate": rate, "misclicks": misclicks}


def _score_gating(actions: List[Dict[str, Any]]) -> tuple[int, Dict[str, Any]]:
    gate_reasons = {
        "precheck_failed",
        "hover_check_missing",
        "low_confidence_hover_missing",
        "occluded",
        "double_check_hover_mismatch",
    }
    gated = 0
    total = 0
    for entry in actions:
        result = entry.get("result", {})
        if not isinstance(result, dict):
            continue
        total += 1
        reason = str(result.get("failure_reason", "")).lower()
        if reason in gate_reasons:
            gated += 1
    score = 1
    if gated > 0:
        score = 3
    if gated >= 3:
        score = 4
    return score, {"gated_actions": gated, "actions": total}


def _score_rhythm(timing_entries: List[Dict[str, Any]]) -> tuple[int, Dict[str, Any]]:
    flags = {"fatigue_drift_ms", "burst_rest_ms", "idle_pause_ms", "idle_recovery_ms"}
    present = set()
    for timing in timing_entries:
        if not isinstance(timing, dict):
            continue
        for field in flags:
            if field in timing:
                present.add(field)
    score = 1
    if len(present) >= 1:
        score = 3
    if len(present) >= 2:
        score = 4
    return score, {"rhythm_fields_present": sorted(present)}


def _score_camera(actions: List[Dict[str, Any]], motion_entries: List[Dict[str, Any]]) -> tuple[int, Dict[str, Any]]:
    camera_actions = 0
    for entry in actions:
        intent = entry.get("intent", {})
        if isinstance(intent, dict) and intent.get("action_type") == "camera":
            camera_actions += 1
    motion_fields = {"camera_nudge_px", "camera_overrotate_px", "camera_micro_adjust_px"}
    present = set()
    for motion in motion_entries:
        if not isinstance(motion, dict):
            continue
        for field in motion_fields:
            if field in motion:
                present.add(field)
    score = 1
    if camera_actions and present:
        score = 3
    if "camera_micro_adjust_px" in present:
        score = 4
    return score, {"camera_actions": camera_actions, "camera_fields_present": sorted(present)}


def _score_typing(timing_entries: List[Dict[str, Any]]) -> tuple[int, Dict[str, Any]]:
    corrections = 0
    bursts = 0
    overlaps = 0
    for timing in timing_entries:
        if not isinstance(timing, dict):
            continue
        if isinstance(timing.get("typing_corrections"), (int, float)):
            corrections += int(timing["typing_corrections"])
        if isinstance(timing.get("typing_bursts"), (int, float)):
            bursts += int(timing["typing_bursts"])
        if isinstance(timing.get("typing_overlap_avg_ms"), (int, float)):
            overlaps += 1
    score = 1
    if bursts > 0:
        score = 3
    if corrections > 0 and overlaps > 0:
        score = 4
    return score, {"typing_bursts": bursts, "typing_corrections": corrections, "typing_overlap_samples": overlaps}


def _score_decision(execution_summary: Dict[str, Any]) -> tuple[int, Dict[str, Any]]:
    total = int(execution_summary.get("count", 0) or 0)
    success = int(execution_summary.get("success_count", 0) or 0)
    rate = success / total if total else 0.0
    score = 1
    if total == 0:
        return 0, {"success_rate": 0.0, "actions": 0}
    if rate >= 0.75:
        score = 3
    if rate >= 0.9:
        score = 4
    return score, {"success_rate": rate, "actions": total}


def _score_chat() -> tuple[int, Dict[str, Any]]:
    return 0, {"chat_samples": 0}


def score(
    actions_path: Path,
    context_path: Path,
    execution_path: Path,
) -> Dict[str, Any]:
    actions = _read_jsonl(actions_path)
    context = _read_jsonl(context_path)
    execution_summary = _read_json(execution_path)
    timing_entries = [entry.get("timing", {}) for entry in context if isinstance(entry, dict)]
    motion_entries = [entry.get("motion", {}) for entry in context if isinstance(entry, dict)]

    scores = {}
    evidence = {}

    scores["timing"] , evidence["timing"] = _score_timing(timing_entries)
    scores["motion"] , evidence["motion"] = _score_motion(motion_entries)
    scores["error"] , evidence["error"] = _score_error(actions)
    scores["gating"] , evidence["gating"] = _score_gating(actions)
    scores["rhythm"] , evidence["rhythm"] = _score_rhythm(timing_entries)
    scores["camera"] , evidence["camera"] = _score_camera(actions, motion_entries)
    scores["typing"] , evidence["typing"] = _score_typing(timing_entries)
    scores["decision"] , evidence["decision"] = _score_decision(execution_summary)
    scores["chat"] , evidence["chat"] = _score_chat()

    weights = {
        "timing": 0.20,
        "motion": 0.18,
        "error": 0.10,
        "gating": 0.12,
        "rhythm": 0.10,
        "camera": 0.08,
        "typing": 0.07,
        "decision": 0.10,
        "chat": 0.05,
    }
    total = 0.0
    for key, weight in weights.items():
        total += weight * (scores.get(key, 0) / 5.0)
    return {
        "scores": scores,
        "total": round(total * 100.0, 2),
        "evidence": evidence,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Score human mimicry rubric from logs.")
    parser.add_argument("--actions", default=str(DEFAULT_ACTIONS))
    parser.add_argument("--context", default=str(DEFAULT_CONTEXT))
    parser.add_argument("--execution", default=str(DEFAULT_EXECUTION))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--scenario", default="")
    parser.add_argument("--profile", default="")
    args = parser.parse_args()

    report = score(Path(args.actions), Path(args.context), Path(args.execution))
    payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "run_id": args.run_id or "",
        "scenario": args.scenario or "",
        "profile": args.profile or "",
        "rubric": report,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
