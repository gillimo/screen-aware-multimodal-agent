import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Replay viewer (summary)")
    parser.add_argument("report_path")
    args = parser.parse_args()

    path = Path(args.report_path)
    if not path.exists():
        print(f"Missing report: {path}")
        return

    report = json.loads(path.read_text(encoding="utf-8"))
    required = {"fps_target", "duration_s", "frames_captured"}
    if not required.issubset(report.keys()):
        print("Not a capture session report; missing required fields.")
        return

    print("Replay summary")
    print(f"- fps_target: {report.get('fps_target')}")
    print(f"- duration_s: {report.get('duration_s')}")
    print(f"- frames_captured: {report.get('frames_captured')}")
    print(f"- dropped_frames: {report.get('dropped_frames')}")
    print(f"- avg_capture_latency_ms: {report.get('avg_capture_latency_ms')}")
    print(f"- max_capture_latency_ms: {report.get('max_capture_latency_ms')}")
    if "focused_frames" in report:
        print(f"- focused_frames: {report.get('focused_frames')}")


if __name__ == "__main__":
    main()
