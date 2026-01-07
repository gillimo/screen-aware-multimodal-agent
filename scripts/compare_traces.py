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
    args = parser.parse_args()

    agent_rows = _load_trace(args.agent)
    human_rows = _load_trace(args.human)

    agent_summary = summarize(agent_rows)
    human_summary = summarize(human_rows)

    print("Trace comparison")
    print(f"- agent_count: {agent_summary['count']}")
    print(f"- human_count: {human_summary['count']}")
    print(f"- agent_reaction_ms_mean: {agent_summary['reaction_ms_mean']}")
    print(f"- human_reaction_ms_mean: {human_summary['reaction_ms_mean']}")


if __name__ == "__main__":
    main()
