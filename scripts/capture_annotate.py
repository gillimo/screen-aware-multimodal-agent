import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Capture/annotate dataset scaffolding")
    parser.add_argument("--out", default="data/annotations")
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    out_dir = (root / args.out).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = out_dir / f"session_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "dataset_id": f"session_{stamp}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "note": args.note,
        "files": {
            "ui_labels": "ui_labels.jsonl",
            "ocr_labels": "ocr_labels.jsonl",
            "frames": "frames/",
        },
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (run_dir / "ui_labels.jsonl").write_text("", encoding="utf-8")
    (run_dir / "ocr_labels.jsonl").write_text("", encoding="utf-8")
    (run_dir / "frames").mkdir(exist_ok=True)
    print(f"Created annotation session at {run_dir}")


if __name__ == "__main__":
    main()
