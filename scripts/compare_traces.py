import argparse
import json
from pathlib import Path


def _load_trace(path):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def _load_thresholds(path):
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_report(path):
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _mean(values):
    return sum(values) / len(values) if values else 0


def summarize(rows):
    counts = {}
    reaction = []
    for row in rows:
        action = row.get("action_type") or row.get("type") or "unknown"
        counts[action] = counts.get(action, 0) + 1
        timing = row.get("timing", {})
        if isinstance(timing, dict) and "reaction_ms" in timing:
            reaction.append(timing["reaction_ms"])
    return {
        "count": sum(counts.values()),
        "actions": counts,
        "reaction_ms_mean": _mean(reaction),
    }


def main():
    parser = argparse.ArgumentParser(description="Compare agent vs human traces")
    parser.add_argument("--agent", required=True)
    parser.add_argument("--human", required=True)
    parser.add_argument(
        "--thresholds",
        default="data/human_equivalence_thresholds.json",
        help="Optional thresholds JSON for pass/fail checks.",
    )
    parser.add_argument(
        "--baseline-report",
        default="",
        help="Optional baseline report JSON to compute regression deltas.",
    )
    parser.add_argument("--out", default="", help="Optional JSON output path for summary report.")
    args = parser.parse_args()

    agent_rows = _load_trace(args.agent)
    human_rows = _load_trace(args.human)

    agent_summary = summarize(agent_rows)
    human_summary = summarize(human_rows)
    thresholds = _load_thresholds(args.thresholds)
    p3 = thresholds.get("p3", {}) if isinstance(thresholds, dict) else {}
    checks = {}
    if isinstance(p3, dict):
        latency_max = p3.get("latency_ms_max")
        if isinstance(latency_max, (int, float)):
            checks["agent_reaction_ms_max"] = {
                "value": agent_summary["reaction_ms_mean"],
                "limit": float(latency_max),
                "pass": agent_summary["reaction_ms_mean"] <= float(latency_max),
            }
        delta_limit = p3.get("reaction_ms_mean_delta_max")
        if isinstance(delta_limit, (int, float)):
            delta = abs(agent_summary["reaction_ms_mean"] - human_summary["reaction_ms_mean"])
            checks["reaction_ms_mean_delta_max"] = {
                "value": delta,
                "limit": float(delta_limit),
                "pass": delta <= float(delta_limit),
            }
        count_limit = p3.get("action_count_delta_max")
        if isinstance(count_limit, (int, float)):
            delta = abs(agent_summary["count"] - human_summary["count"])
            checks["action_count_delta_max"] = {
                "value": delta,
                "limit": float(count_limit),
                "pass": delta <= float(count_limit),
            }
    report = {
        "agent": agent_summary,
        "human": human_summary,
        "checks": checks,
    }
    baseline = _load_report(args.baseline_report)
    if isinstance(baseline, dict):
        regression = {}
        baseline_agent = baseline.get("agent", {}) if isinstance(baseline.get("agent"), dict) else {}
        baseline_human = baseline.get("human", {}) if isinstance(baseline.get("human"), dict) else {}
        for key in ("count", "reaction_ms_mean"):
            if key in agent_summary and key in baseline_agent:
                regression[f"agent_{key}_delta"] = agent_summary[key] - baseline_agent[key]
            if key in human_summary and key in baseline_human:
                regression[f"human_{key}_delta"] = human_summary[key] - baseline_human[key]
        baseline_checks = baseline.get("checks", {}) if isinstance(baseline.get("checks"), dict) else {}
        check_regressions = {}
        for check_id, entry in checks.items():
            if check_id not in baseline_checks:
                continue
            prev_pass = bool(baseline_checks.get(check_id, {}).get("pass"))
            current_pass = bool(entry.get("pass"))
            if prev_pass and not current_pass:
                check_regressions[check_id] = "regressed"
        if check_regressions:
            regression["check_regressions"] = check_regressions
        report["regression"] = regression

    print("Trace comparison")
    print(f"- agent_count: {agent_summary['count']}")
    print(f"- human_count: {human_summary['count']}")
    print(f"- agent_reaction_ms_mean: {agent_summary['reaction_ms_mean']}")
    print(f"- human_reaction_ms_mean: {human_summary['reaction_ms_mean']}")
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote report to {args.out}")


if __name__ == "__main__":
    main()
