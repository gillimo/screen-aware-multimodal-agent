import argparse
import json
from pathlib import Path


def _load_json(path):
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main():
    parser = argparse.ArgumentParser(description="Human equivalence report")
    parser.add_argument("--compare", default="", help="Path to compare_traces JSON output.")
    parser.add_argument("--calibration", default="", help="Path to calibration summary JSON.")
    parser.add_argument(
        "--out",
        default="data/human_equivalence_report.json",
        help="Output path for the combined human-equivalence report JSON.",
    )
    args = parser.parse_args()

    compare = _load_json(args.compare)
    calibration = _load_json(args.calibration)

    report = {
        "compare": compare,
        "calibration": calibration,
        "notes": "auto-generated summary",
    }
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote report to {args.out}")


if __name__ == "__main__":
    main()
