import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Human session capture scaffold")
    parser.add_argument("--out", default="data/human_sessions")
    parser.add_argument("--task-id", default="session_task")
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    out_dir = (root / args.out).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    session_dir = out_dir / f"session_{stamp}"
    session_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "dataset_id": f"baseline_{stamp}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "note": args.note,
        "tasks": [
            {
                "task_id": args.task_id,
                "session_ids": [f"sess_{stamp}"],
                "annotations": {
                    "ui_labels": "ui_labels.jsonl",
                    "ocr_labels": "ocr_labels.jsonl",
                },
            }
        ],
        "files": {
            "input_traces": ["input_trace.jsonl"],
            "video": ["session_video.mp4"],
            "snapshots": ["snapshots.jsonl"],
        },
    }

    (session_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (session_dir / "input_trace.jsonl").write_text("", encoding="utf-8")
    (session_dir / "snapshots.jsonl").write_text("", encoding="utf-8")
    (session_dir / "ui_labels.jsonl").write_text("", encoding="utf-8")
    (session_dir / "ocr_labels.jsonl").write_text("", encoding="utf-8")
    print(f"Created human session scaffold at {session_dir}")


if __name__ == "__main__":
    main()
