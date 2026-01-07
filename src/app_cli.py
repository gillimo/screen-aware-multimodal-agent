import argparse
import json
import gzip
from pathlib import Path
from datetime import datetime

from src.engine import (
    load_json,
    validate_state,
    migrate_state,
    compute_ratings,
    detect_bottlenecks,
    build_quest_graph,
    generate_plan,
    compare_paths,
    risk_score,
    onboarding_steps,
    beginner_quest_bundle,
    gear_food_recs,
    money_guide,
    teleport_checklist,
    glossary_terms,
    boss_readiness,
    efficiency_benchmarks,
    gear_upgrade_optimizer,
    time_to_goal_estimate,
    ironman_constraints,
    scheduler_tasks,
)
from src.schema_validation import (
    validate_snapshot_schema,
    validate_humanization_schema,
    validate_decision_trace_schema,
    validate_human_kpi_log_schema,
)
from src.chat_filter import should_respond_to_chat
from src.perception import find_window, capture_frame, capture_session
from src.local_model import build_prompt, build_decision_prompt, run_local_model, load_config
from src.model_output import extract_json, validate_planner_output, log_decision, validate_decision_trace, purge_decisions
from src.humanization import list_profiles, get_profile, get_active_profile
from src.human_likeness import score_from_traces, write_kpi, validate_kpi_schema, append_kpi_log

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
STATE_PATH = DATA_DIR / "state.json"
REF_PATH = DATA_DIR / "reference.json"
SNAPSHOT_DIR = DATA_DIR / "snapshots"


def save_log(message):
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"run_{stamp}.log"
    log_path.write_text(message, encoding="utf-8")


def write_overlay(state):
    plan = generate_plan(state)
    ratings, _reasons = compute_ratings(state)
    blockers = detect_bottlenecks(state)
    lines = []
    lines.append("Plan:")
    for item in plan.get("short", [])[:3]:
        lines.append(f"- {item.get('task')}")
    lines.append("Ratings:")
    for key, val in ratings.items():
        lines.append(f"- {key.replace('_', ' ')} {val}")
    if blockers:
        lines.append("Blockers:")
        for b in blockers[:3]:
            lines.append(f"- {b}")
    overlay_path = ROOT / "data" / "overlay.txt"
    overlay_path.write_text("\n".join(lines), encoding="utf-8")


def compute_skill_average(skills):
    if not skills:
        return 0
    vals = list(skills.values())
    return sum(vals) / max(1, len(vals))


def rating_summary(state):
    ratings, _reasons = compute_ratings(state)
    return ratings


def cmd_status(state):
    account = state.get("account", {})
    skills = state.get("skills", {})
    print("Account status")
    print(f"- Name: {account.get('name', 'Unknown')}")
    print(f"- Mode: {account.get('mode', 'main')}")
    print(f"- Combat level: {account.get('combat_level', 'n/a')}")
    print(f"- GP: {account.get('gp', 0)}")
    print(f"- Avg skill: {compute_skill_average(skills):.1f}")
    goals = state.get("goals", {})
    print(f"- Goals (short): {', '.join(goals.get('short', []))}")


def cmd_ratings(state):
    ratings, reasons = compute_ratings(state)
    print("Ratings")
    for k, v in ratings.items():
        print(f"- {k.replace('_', ' ').title()}: {v}/100")
        for r in reasons.get(k, [])[:3]:
            print(f"  reason: {r}")


def cmd_plan(state, model_message=None, prefer_model=False):
    if model_message or prefer_model:
        if not model_message:
            model_message = "plan next step"
        cfg = load_config()
        prompt = build_decision_prompt(state, model_message)
        reply = run_local_model(prompt)
        payload = extract_json(reply)
        if payload is None and cfg.get("strict_json", False):
            reply = run_local_model(prompt)
            payload = extract_json(reply)
        if payload is None:
            if cfg.get("strict_json", False):
                print("Model output is not valid JSON. Aborting.")
                return
            print("Model output is not valid JSON. Falling back to heuristic plan.")
            plan = generate_plan(state)
        else:
            errors = validate_planner_output(payload)
            if errors:
                if cfg.get("strict_json", False):
                    print("Model output schema errors. Aborting.")
                    for e in errors:
                        print(f"- {e}")
                    return
                print("Model output schema errors. Falling back to heuristic plan.")
                plan = generate_plan(state)
            else:
                log_decision(payload, "plan", model_message)
                rationale = payload.get("rationale", [])
                plan = {
                    "short": [{
                        "task": payload.get("intent", "model_plan"),
                        "why": "; ".join(rationale) if rationale else "model_decision",
                        "time": "unknown",
                        "prereqs": [],
                    }],
                    "mid": [],
                    "long": [],
                }
    else:
        plan = generate_plan(state)
    print("Plan")
    for horizon in ["short", "mid", "long"]:
        print(f"{horizon.title()} horizon:")
        for idx, item in enumerate(plan.get(horizon, []), start=1):
            prereqs = ", ".join(item.get("prereqs", [])) or "none"
            print(f" {idx}) {item.get('task')} ({item.get('time')})")
            print(f"    why: {item.get('why')}; prereqs: {prereqs}")
    print("Alternate paths:")
    for opt in compare_paths(state):
        print(f"- {opt['path']}: {opt['tradeoff']} ({opt['notes']})")


def cmd_quests(state):
    ref = load_json(REF_PATH, {})
    data = ref.get("quests", [])
    incomplete = set(state.get("quests", {}).get("not_started", [])) | set(state.get("quests", {}).get("in_progress", []))
    print("Quest guidance")
    for q in data:
        name = q.get("name")
        if name in incomplete:
            reqs = q.get("quest_reqs", [])
            skills = q.get("skill_reqs", {})
            print(f"- {name}")
            if reqs:
                print(f"  prereq quests: {', '.join(reqs)}")
            if skills:
                print(f"  skill reqs: {', '.join([f'{k} {v}' for k, v in skills.items()])}")


def cmd_diaries(state):
    diaries = load_json(REF_PATH, {}).get("diaries", [])
    current = state.get("diaries", {})
    print("Diary guidance")
    for d in diaries:
        region = d.get("region")
        tiers = d.get("tiers", [])
        cur = current.get(region, "none")
        print(f"- {region}: current {cur}, tiers {', '.join(tiers)}")


def cmd_gear(state):
    tiers = load_json(REF_PATH, {}).get("gear_tiers", {})
    gear = state.get("gear", {})
    print("Gear guidance")
    for style, ladder in tiers.items():
        cur = ", ".join(gear.get(style, [])) or "none"
        print(f"- {style}: current {cur}; ladder: {', '.join(ladder)}")


def cmd_money(state):
    gp = state.get("account", {}).get("gp", 0)
    print("Money guidance")
    print(f"- Current GP: {gp}")
    print("- Methods are based on local reference data (stub).")


def cmd_slayer(_state):
    print("Slayer guidance")
    print("- Choose a master based on combat level and gear.")


def cmd_bossing(state):
    reqs = load_json(REF_PATH, {}).get("boss_requirements", [])
    print("Bossing guidance")
    for r in reqs:
        print(f"- {r.get('name')}: requires {', '.join(r.get('reqs', []))}")


def cmd_profile(state):
    ratings, _reasons = compute_ratings(state)
    blockers = detect_bottlenecks(state)
    print("Profile summary")
    print(f"- Ratings: {ratings}")
    print(f"- Bottlenecks: {', '.join(blockers) if blockers else 'none'}")


def cmd_import(path):
    state = load_json(Path(path), {})
    state = migrate_state(state)
    errors = validate_state(state)
    if errors:
        print("Import failed:")
        for e in errors:
            print(f"- {e}")
        return
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print("Import complete.")


def cmd_export(state, target):
    Path(target).write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"Exported to {target}")


def cmd_checklist(_state):
    print("Daily checklist")
    print("- Farm runs (if farming unlocked)")
    print("- Tears of Guthix (weekly)")
    print("- Birdhouse runs (if unlocked)")


def cmd_onboarding(state):
    print("Onboarding steps")
    for idx, step in enumerate(onboarding_steps(state), start=1):
        print(f"{idx}) {step}")


def cmd_beginner_bundle(state):
    print("Beginner quest bundle")
    for idx, q in enumerate(beginner_quest_bundle(state), start=1):
        print(f"{idx}) {q.get('name')}: {q.get('why')}")


def cmd_gear_food(state):
    rec = gear_food_recs(state)
    print("Gear and food recommendations")
    print(f"- Suggested food: {rec.get('food')}")
    tiers = rec.get("gear_tiers", {})
    for style, ladder in tiers.items():
        print(f"- {style}: {', '.join(ladder)}")


def cmd_money_guide(state):
    print("Beginner money guide")
    for m in money_guide(state):
        print(f"- {m.get('method')} ({m.get('gp_hr')} gp/hr, risk {m.get('risk')})")


def cmd_teleports(state):
    data = teleport_checklist(state)
    print("Teleport checklist")
    for phase, items in data.get("checklist", {}).items():
        print(f"- {phase}: {', '.join(items)}")
    print(f"Current: {', '.join(data.get('current', []))}")


def cmd_glossary(_state):
    print("Glossary")
    for item in glossary_terms():
        print(f"- {item.get('term')}: {item.get('def')}")


def cmd_readiness(state):
    print("Boss readiness")
    for r in boss_readiness(state):
        status = "ready" if r.get("reqs_ok") and r.get("stats_ok") else "not ready"
        print(f"- {r.get('name')}: {status}")


def cmd_benchmarks(_state):
    print("Efficiency benchmarks")
    for b in efficiency_benchmarks():
        print(f"- {b.get('skill')}: {b.get('method')} {b.get('xp_hr')} xp/hr")


def cmd_upgrades(state):
    print("Gear upgrade optimizer")
    for u in gear_upgrade_optimizer(state):
        print(f"- {u.get('style')}: {u.get('from')} -> {u.get('to')} (gp {u.get('gp')}, impact {u.get('impact')})")


def cmd_estimate(state):
    print("Time-to-goal estimates")
    for e in time_to_goal_estimate(state):
        print(f"- {e.get('goal')}: {e.get('hours')}h")


def cmd_scheduler(state):
    sched = scheduler_tasks(state)
    print("Scheduler")
    print("- daily: " + ", ".join(sched.get("daily", [])))
    print("- weekly: " + ", ".join(sched.get("weekly", [])))


def cmd_risk(state):
    print(f"Risk score: {risk_score(state)}/100")
    if ironman_constraints(state):
        print("Ironman constraints enabled: avoid buy-only methods.")


def cmd_pathcompare(state):
    print("Path comparison")
    for opt in compare_paths(state):
        print(f"- {opt['path']}: {opt['tradeoff']} ({opt['notes']})")


def cmd_questgraph(state):
    print("Quest dependency graph")
    graph = build_quest_graph(state)
    for q, reqs in graph.items():
        if reqs:
            print(f"- {q}: {', '.join(reqs)}")


def cmd_gui(_state):
    from gui.app import run_app
    run_app()


def _load_roi_config(path):
    if not path:
        return {}
    roi_path = Path(path)
    if not roi_path.exists():
        print(f"ROI config not found: {path}")
        return {}
    data = load_json(roi_path, {})
    return data if isinstance(data, dict) else {}


def cmd_capture(title_contains, fps, duration_s, roi_path):
    window = find_window(title_contains)
    if not window:
        print(f"No window found matching: {title_contains}")
        return

    roi = _load_roi_config(roi_path)
    if fps > 0 and duration_s > 0:
        report = capture_session(window.bounds, fps, duration_s, window.handle)
        report["window_title"] = window.title
        report["bounds"] = {
            "x": window.bounds[0],
            "y": window.bounds[1],
            "width": window.bounds[2] - window.bounds[0],
            "height": window.bounds[3] - window.bounds[1],
        }
        report["roi"] = roi
        SNAPSHOT_DIR.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = SNAPSHOT_DIR / f"capture_session_{stamp}.json"
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Captured session report to {out_path}")
        return

    frame = capture_frame(window.bounds)
    snapshot = {
        "timestamp": frame["timestamp"],
        "session_id": "local_capture",
        "client": {
            "window_title": window.title,
            "bounds": frame["bounds"],
            "focused": window.focused,
            "scale": 1.0,
            "fps": 0,
            "capture_latency_ms": frame["capture_latency_ms"],
        },
        "roi": roi,
        "ui": {
            "open_interface": "none",
            "selected_tab": "unknown",
            "cursor_state": "default",
            "hover_text": "",
            "elements": [],
            "dialogue_options": [],
        },
        "ocr": [],
        "cues": {
            "animation_state": "unknown",
            "highlight_state": "none",
            "modal_state": "none",
            "hover_text": "",
        },
        "derived": {
            "location": {},
            "activity": {},
            "combat": {},
        },
        "account": {
            "name": "",
            "membership_status": "unknown",
            "skills": {},
            "inventory": [],
            "equipment": {},
            "resources": {},
        },
    }
    errors = validate_snapshot_schema(snapshot)
    if errors:
        print("Snapshot validation errors:")
        for e in errors:
            print(f"- {e}")
        return

    SNAPSHOT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = SNAPSHOT_DIR / f"snapshot_{stamp}.json"
    out_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"Captured snapshot to {out_path}")


def _load_chat_lines(path):
    if not path:
        return []
    chat_path = Path(path)
    if not chat_path.exists():
        print(f"Chat log not found: {path}")
        return []
    return [line.strip() for line in chat_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def cmd_model(state, message, chat_log):
    if not message:
        print("Message required. Use --message \"...\".")
        return
    chat_lines = _load_chat_lines(chat_log)
    if chat_lines and not should_respond_to_chat(chat_lines):
        print("Chat suppressed: random event detected.")
        return
    prompt = build_prompt(state, message)
    reply = run_local_model(prompt)
    print("Model reply")
    print(reply)


def cmd_model_decision(state, message):
    if not message:
        print("Message required. Use --message \"...\".")
        return
    prompt = build_decision_prompt(state, message)
    reply = run_local_model(prompt)
    payload = extract_json(reply)
    if payload is None:
        cfg = load_config()
        if cfg.get("strict_json", False):
            reply = run_local_model(prompt)
            payload = extract_json(reply)
        if payload is None:
            print("Model output is not valid JSON.")
            print(reply)
            return
    if payload is None:
        print(reply)
        return
    errors = validate_planner_output(payload)
    if errors:
        print("Model output schema errors:")
        for e in errors:
            print(f"- {e}")
        return
    log_decision(payload, "model-decision", message)
    print(json.dumps(payload, indent=2))


def cmd_profiles(profile_name):
    if profile_name:
        profile = get_profile(profile_name)
        if not profile:
            print(f"Profile not found: {profile_name}")
            return
        print(json.dumps(profile, indent=2))
        return
    profiles = list_profiles()
    print("Humanization profiles:")
    for name in profiles:
        print(f"- {name}")


def cmd_profile_select(name):
    if not name:
        print("Profile name required. Use --profile <name>.")
        return
    if not get_profile(name):
        print(f"Profile not found: {name}")
        return
    cfg = load_config()
    cfg["active_profile"] = name
    path = DATA_DIR / "local_model.json"
    path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(f"Active profile set to {name}")


def cmd_validate_profiles(path):
    target = Path(path) if path else (DATA_DIR / "humanization_profiles.json")
    profiles = load_json(target, {})
    errors = validate_humanization_schema(profiles)
    if errors:
        print("Humanization profile schema errors:")
        for e in errors:
            print(f"- {e}")
        return
    print("Humanization profile schema ok.")


def cmd_validate_model_output(path):
    if not path:
        print("Model output path required. Use --model-output <path>.")
        return
    text = Path(path).read_text(encoding="utf-8")
    payload = extract_json(text)
    if payload is None:
        print("Model output is not valid JSON.")
        return
    errors = validate_planner_output(payload)
    if errors:
        print("Model output schema errors:")
        for e in errors:
            print(f"- {e}")
        return
    print("Model output schema ok.")


def cmd_validate_decision_trace(path):
    if not path:
        print("Trace path required. Use --trace-path <path>.")
        return
    errors = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                errors.append(f"line {idx}: invalid JSON")
                continue
            for err in validate_decision_trace_schema(entry):
                errors.append(f"line {idx}: {err}")
            for err in validate_decision_trace(entry):
                errors.append(f"line {idx}: {err}")
    if errors:
        print("Decision trace validation errors:")
        for e in errors:
            print(f"- {e}")
        return
    print("Decision trace validation ok.")


def cmd_decision_replay(path):
    if not path:
        print("Trace path required. Use --trace-path <path>.")
        return
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            payload = entry.get("payload", {})
            intent = payload.get("intent", "unknown")
            confidence = payload.get("confidence", "n/a")
            print(f"- {intent} (confidence {confidence})")


def cmd_decision_tail(path, limit):
    if not path:
        print("Trace path required. Use --trace-path <path>.")
        return
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    for line in lines[-limit:]:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue
        payload = entry.get("payload", {})
        intent = payload.get("intent", "unknown")
        print(f"- {intent}")


def cmd_decision_export(path, out_path):
    if not path or not out_path:
        print("Trace and output paths required. Use --trace-path and --out.")
        return
    data = Path(path).read_text(encoding="utf-8")
    with gzip.open(out_path, "wt", encoding="utf-8") as handle:
        handle.write(data)
    print(f"Exported decision trace to {out_path}")


def cmd_purge_decisions(days):
    if days <= 0:
        print("Days must be > 0. Use --days <n>.")
        return
    removed = purge_decisions(days)
    print(f"Purged {removed} decision entries older than {days} days.")

def cmd_score_human(traces_path):
    if not traces_path:
        print("Trace path required. Use --traces <path>.")
        return
    traces = []
    with Path(traces_path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                traces.append(json.loads(line))
            except Exception:
                continue
    result = score_from_traces(traces)
    print(json.dumps(result, indent=2))


def cmd_score_human_write(traces_path, out_path):
    if not traces_path or not out_path:
        print("Trace and output paths required. Use --traces and --out.")
        return
    traces = []
    with Path(traces_path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                traces.append(json.loads(line))
            except Exception:
                continue
    result = write_kpi(traces, out_path)
    errors = validate_kpi_schema(result)
    if errors:
        print("KPI schema errors:")
        for e in errors:
            print(f"- {e}")
        return
    print(json.dumps(result, indent=2))


def cmd_validate_kpi(path):
    if not path:
        print("KPI path required. Use --kpi <path>.")
        return
    payload = load_json(Path(path), {})
    errors = validate_kpi_schema(payload)
    if errors:
        print("KPI schema errors:")
        for e in errors:
            print(f"- {e}")
        return
    print("KPI schema ok.")


def cmd_kpi_append(path, out_path):
    if not path or not out_path:
        print("KPI input and output required. Use --kpi and --out.")
        return
    payload = load_json(Path(path), {})
    errors = validate_kpi_schema(payload)
    if errors:
        print("KPI schema errors:")
        for e in errors:
            print(f"- {e}")
        return
    entry = append_kpi_log(payload, out_path)
    log_errors = validate_human_kpi_log_schema(entry)
    if log_errors:
        print("KPI log schema errors:")
        for e in log_errors:
            print(f"- {e}")
        return
    print(json.dumps(entry, indent=2))


def cmd_decision_summary(path, out_path):
    if not path:
        print("Trace path required. Use --trace-path <path>.")
        return
    intents = {}
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            payload = entry.get("payload", {})
            intent = payload.get("intent", "unknown")
            intents[intent] = intents.get(intent, 0) + 1
    summary = {"intents": intents}
    if out_path:
        Path(out_path).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def cmd_profile_status():
    profile = get_active_profile()
    if not profile:
        print("Active profile not set.")
        return
    print(json.dumps(profile, indent=2))
def cmd_validate(state, snapshot_path):
    errors = validate_state(state)
    if errors:
        print("State validation errors:")
        for e in errors:
            print(f"- {e}")
    else:
        print("State validation ok.")

    if snapshot_path:
        snap = load_json(Path(snapshot_path), {})
        snap_errors = validate_snapshot_schema(snap)
        if snap_errors:
            print("Snapshot validation errors:")
            for e in snap_errors:
                print(f"- {e}")
        else:
            print("Snapshot validation ok.")


def main():
    parser = argparse.ArgumentParser(description="OSRS Coach CLI")
    parser.add_argument("command", nargs="?", default="status")
    parser.add_argument("--state", default=str(STATE_PATH))
    parser.add_argument("--snapshot", default="")
    parser.add_argument("--title", default="Old School RuneScape")
    parser.add_argument("--fps", type=float, default=0)
    parser.add_argument("--seconds", type=float, default=0)
    parser.add_argument("--roi", default="")
    parser.add_argument("--message", default="")
    parser.add_argument("--model-message", default="")
    parser.add_argument("--chat-log", default="")
    parser.add_argument("--profile", default="")
    parser.add_argument("--profiles-path", default="")
    parser.add_argument("--model-output", default="")
    parser.add_argument("--traces", default="")
    parser.add_argument("--trace-path", default="")
    parser.add_argument("--days", type=int, default=0)
    parser.add_argument("--out", default="")
    parser.add_argument("--kpi", default="")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    cmd = args.command.lower()
    if cmd == "validate-snapshot":
        if not args.snapshot:
            print("Snapshot path required. Use --snapshot <path>.")
            return
        snap = load_json(Path(args.snapshot), {})
        snap_errors = validate_snapshot_schema(snap)
        if snap_errors:
            print("Snapshot validation errors:")
            for e in snap_errors:
                print(f"- {e}")
        else:
            print("Snapshot validation ok.")
        return

    state_path = Path(args.state)
    state = load_json(state_path, {})
    if not state:
        print("State file missing or empty. Edit data/state.json first.")
        return
    state = migrate_state(state)
    errors = validate_state(state)
    if errors:
        print("State validation errors:")
        for e in errors:
            print(f"- {e}")
        return

    if cmd == "status":
        cmd_status(state)
    elif cmd == "ratings":
        cmd_ratings(state)
    elif cmd == "plan":
        cfg = load_config()
        prefer_model = cfg.get("plan_default", "heuristic") == "model"
        cmd_plan(state, args.model_message, prefer_model=prefer_model)
    elif cmd == "quests":
        cmd_quests(state)
    elif cmd == "diaries":
        cmd_diaries(state)
    elif cmd == "gear":
        cmd_gear(state)
    elif cmd == "money":
        cmd_money(state)
    elif cmd == "slayer":
        cmd_slayer(state)
    elif cmd == "bossing":
        cmd_bossing(state)
    elif cmd == "profile":
        cmd_profile(state)
    elif cmd == "import":
        cmd_import(state_path)
    elif cmd == "export":
        cmd_export(state, str(ROOT / "data" / "export_state.json"))
    elif cmd == "checklist":
        cmd_checklist(state)
    elif cmd == "onboarding":
        cmd_onboarding(state)
    elif cmd == "beginner":
        cmd_beginner_bundle(state)
    elif cmd == "gearfood":
        cmd_gear_food(state)
    elif cmd == "moneyguide":
        cmd_money_guide(state)
    elif cmd == "teleports":
        cmd_teleports(state)
    elif cmd == "glossary":
        cmd_glossary(state)
    elif cmd == "readiness":
        cmd_readiness(state)
    elif cmd == "benchmarks":
        cmd_benchmarks(state)
    elif cmd == "upgrades":
        cmd_upgrades(state)
    elif cmd == "estimate":
        cmd_estimate(state)
    elif cmd == "scheduler":
        cmd_scheduler(state)
    elif cmd == "risk":
        cmd_risk(state)
    elif cmd == "pathcompare":
        cmd_pathcompare(state)
    elif cmd == "questgraph":
        cmd_questgraph(state)
    elif cmd == "gui":
        cmd_gui(state)
    elif cmd == "capture":
        cmd_capture(args.title, args.fps, args.seconds, args.roi)
    elif cmd == "demo":
        cmd_status(state)
        cmd_ratings(state)
        cmd_plan(state)
    elif cmd == "validate":
        cmd_validate(state, args.snapshot)
    elif cmd == "model":
        cmd_model(state, args.message, args.chat_log)
    elif cmd == "model-decision":
        cmd_model_decision(state, args.message)
    elif cmd == "profiles":
        cmd_profiles(args.profile)
    elif cmd == "profile-select":
        cmd_profile_select(args.profile)
    elif cmd == "validate-profiles":
        cmd_validate_profiles(args.profiles_path)
    elif cmd == "validate-model-output":
        cmd_validate_model_output(args.model_output)
    elif cmd == "score-human":
        cmd_score_human(args.traces)
    elif cmd == "score-human-write":
        cmd_score_human_write(args.traces, args.out)
    elif cmd == "validate-kpi":
        cmd_validate_kpi(args.kpi)
    elif cmd == "kpi-append":
        cmd_kpi_append(args.kpi, args.out)
    elif cmd == "validate-decision-trace":
        cmd_validate_decision_trace(args.trace_path)
    elif cmd == "decision-replay":
        cmd_decision_replay(args.trace_path)
    elif cmd == "decision-tail":
        cmd_decision_tail(args.trace_path, args.limit)
    elif cmd == "decision-export":
        cmd_decision_export(args.trace_path, args.out)
    elif cmd == "purge-decisions":
        cmd_purge_decisions(args.days)
    elif cmd == "profile-status":
        cmd_profile_status()
    elif cmd == "decision-summary":
        cmd_decision_summary(args.trace_path, args.out)
    else:
        print("Unknown command. Try: status, ratings, plan, quests, diaries, gear, money, slayer, bossing, profile, import, export, checklist, onboarding, beginner, gearfood, moneyguide, teleports, glossary, readiness, benchmarks, upgrades, estimate, scheduler, risk, pathcompare, questgraph, gui, capture, validate, validate-snapshot, model, model-decision, profiles, profile-select, profile-status, validate-profiles, validate-model-output, validate-decision-trace, decision-replay, decision-summary, decision-tail, decision-export, purge-decisions, score-human, score-human-write, validate-kpi, kpi-append")

    write_overlay(state)
    save_log(f"Command: {cmd}\n")


if __name__ == "__main__":
    main()
