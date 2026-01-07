import argparse
import json
from pathlib import Path
from statistics import mean, pstdev


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


def main():
    parser = argparse.ArgumentParser(description="Calibrate timing distributions from traces")
    parser.add_argument("--trace", required=True)
    parser.add_argument("--out", default="data/timing_calibration.json")
    args = parser.parse_args()

    rows = _load_trace(args.trace)
    timing_values = {}
    for row in rows:
        timing = row.get("timing", {})
        if not isinstance(timing, dict):
            continue
        for key, val in timing.items():
            if isinstance(val, (int, float)):
                timing_values.setdefault(key, []).append(val)

    calibrated = {}
    for key, values in timing_values.items():
        calibrated[key] = {
            "mean": mean(values),
            "stdev": pstdev(values) if len(values) > 1 else 0,
            "count": len(values),
        }

    Path(args.out).write_text(json.dumps(calibrated, indent=2), encoding="utf-8")
    print(f"Wrote calibration to {args.out}")


if __name__ == "__main__":
    main()
