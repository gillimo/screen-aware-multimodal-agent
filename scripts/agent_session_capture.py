import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def _copy_if_exists(src: Path, dest: Path) -> bool:
    if not src.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    return True


def main():
    parser = argparse.ArgumentParser(description="Agent session trace capture")
    parser.add_argument("--out", default="data/agent_sessions", help="Output directory for session capture.")
    parser.add_argument("--session-id", default="", help="Optional session id override.")
    parser.add_argument("--note", default="", help="Optional note to store in the manifest.")
    parser.add_argument("--logs-dir", default="logs", help="Directory containing action logs.")
    parser.add_argument("--snapshots-dir", default="data/snapshots", help="Directory containing snapshots.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    out_dir = (root / args.out).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    session_id = args.session_id or f"sess_{stamp}"
    session_dir = out_dir / f"session_{stamp}"
    session_dir.mkdir(parents=True, exist_ok=True)

    logs_dir = (root / args.logs_dir).resolve()
    snapshots_dir = (root / args.snapshots_dir).resolve()

    files = {
        "actions": "actions.jsonl",
        "action_context": "action_context.jsonl",
        "execution_summary": "execution_summary.json",
        "snapshot_latest": "snapshot_latest.json",
    }
    captured = {
        "actions": _copy_if_exists(logs_dir / "actions.jsonl", session_dir / "actions.jsonl"),
        "action_context": _copy_if_exists(logs_dir / "action_context.jsonl", session_dir / "action_context.jsonl"),
        "execution_summary": _copy_if_exists(logs_dir / "execution_summary.json", session_dir / "execution_summary.json"),
        "snapshot_latest": _copy_if_exists(
            snapshots_dir / "snapshot_latest.json",
            session_dir / "snapshot_latest.json",
        ),
    }

    manifest = {
        "dataset_id": f"agent_{stamp}",
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "note": args.note,
        "files": {
            "actions": files["actions"] if captured["actions"] else "",
            "action_context": files["action_context"] if captured["action_context"] else "",
            "execution_summary": files["execution_summary"] if captured["execution_summary"] else "",
            "snapshot_latest": files["snapshot_latest"] if captured["snapshot_latest"] else "",
        },
        "captured": captured,
    }
    (session_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Captured agent session traces at {session_dir}")


if __name__ == "__main__":
    main()
