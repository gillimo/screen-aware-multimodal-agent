import argparse
import json
import gzip
import time
import random
import sys
import uuid
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
    validate_tutorial_state_schema,
    validate_tutorial_decisions_schema,
)
from src.chat_filter import should_respond_to_chat
from src.perception import find_window, capture_frame, capture_session, save_frame, focus_window
from src.local_model import build_prompt, build_decision_prompt, run_local_model, load_config
from src.model_output import extract_json, validate_planner_output, log_decision, validate_decision_trace, purge_decisions
from src.decision_consume import latest_payload, build_action_intents, validate_intents, load_decision_file
from src.targeting import reaim_if_shifted
from src.occlusion import should_wait_for_occlusion, occlusion_reason
from src.interrupts import should_panic_on_chat, InterruptProfile
from src.actions import (
    LiveExecutor,
    ActionLogger,
    ActionResult,
    apply_spacing_delay,
    apply_interrupt_pause,
    pre_action_gate,
    detect_ui_change,
    default_backoff_ms,
    requires_confidence_gate,
    should_confirm_irreversible,
    sample_fatigue_drift_ms,
    sample_burst_rest_ms,
    vary_action_order,
    should_check_hover_text,
    sample_attention_drift_offset,
    focus_recovery_needed,
    build_focus_recovery_intent,
    ActionPolicy,
    ActionRateLimiter,
    policy_check,
    ApprovalPolicy,
    requires_approval,
)
from src.action_context import ActionContextLogger, log_action_context
from src.humanization import list_profiles, get_profile, get_active_profile
from src.human_likeness import score_from_traces, write_kpi, validate_kpi_schema, append_kpi_log
from src.tutorial_loop import run_loop as run_tutorial_loop
from src.randomness import seed_session
from src.idle_behavior import (
    IdleBehaviorProfile,
    should_idle_action,
    choose_idle_action,
    idle_recovery_sequence,
    choose_tab_toggle,
)
from src.ui_scan import scan_panel
from src import input_exec

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


def _write_execution_summary(results):
    if not results:
        return
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    summary = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "count": len(results),
        "results": results,
    }
    (log_dir / "execution_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )


def _client_bounds_tuple(snapshot):
    if not isinstance(snapshot, dict):
        return None
    client = snapshot.get("client", {})
    if not isinstance(client, dict):
        return None
    bounds = client.get("bounds", {})
    if not isinstance(bounds, dict):
        return None
    try:
        x = int(bounds.get("x", 0))
        y = int(bounds.get("y", 0))
        w = int(bounds.get("width", 0))
        h = int(bounds.get("height", 0))
    except Exception:
        return None
    if w <= 0 or h <= 0:
        return None
    return (x, y, x + w, y + h)


def _log_bug_ticket(message: str) -> None:
    bug_path = ROOT / "docs" / "BUG_LOG.md"
    stamp = datetime.utcnow().date().isoformat()
    line = f"- {stamp}: {message}"
    try:
        existing = bug_path.read_text(encoding="utf-8") if bug_path.exists() else "# Bug Log\n\n"
        with bug_path.open("w", encoding="utf-8") as handle:
            handle.write(existing.rstrip() + "\n" + line + "\n")
    except Exception:
        return


def _capture_stuck_artifacts(snapshot, intent_id: str, failure_reason: str) -> None:
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    snapshot_path = log_dir / f"stuck_snapshot_{stamp}.json"
    if isinstance(snapshot, dict):
        snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    bounds = _client_bounds_tuple(snapshot)
    screenshot_path = ""
    if bounds:
        image_path = log_dir / f"stuck_screen_{stamp}.png"
        if save_frame(bounds, str(image_path)):
            screenshot_path = str(image_path)
    note = f"stuck after {intent_id} ({failure_reason}); snapshot={snapshot_path}"
    if screenshot_path:
        note += f"; screenshot={screenshot_path}"
    _log_bug_ticket(note)


def _sleep_ms(delay_ms):
    if not delay_ms or delay_ms <= 0:
        return
    end_time = time.time() + (delay_ms / 1000.0)
    while time.time() < end_time:
        if _escape_pressed():
            print("Escape pressed. Aborting execution.")
            raise SystemExit(1)
        time.sleep(min(0.05, end_time - time.time()))


def _maybe_seed_session(profile, seed_arg):
    seed_value = None
    if seed_arg is not None:
        seed_value = seed_arg
    elif isinstance(profile, dict):
        session_cfg = profile.get("session", {})
        if isinstance(session_cfg, dict) and session_cfg.get("seed") is not None:
            seed_value = session_cfg.get("seed")
    if seed_value is None:
        return None
    try:
        seed_value = int(seed_value)
    except Exception:
        return None
    return seed_session(seed_value)


def _escape_pressed() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import msvcrt
    except ImportError:
        return False
    if msvcrt.kbhit():
        key = msvcrt.getch()
        return key == b"\x1b"
    return False


def _sample_reaction_delay(profile, action_type: str) -> float:
    if not isinstance(profile, dict):
        return 0.0
    timing_cfg = profile.get("timing_ms", {}) if isinstance(profile.get("timing_ms"), dict) else {}
    mean = float(timing_cfg.get("reaction_mean", 180.0))
    stdev = float(timing_cfg.get("reaction_stdev", 60.0))
    reaction_by_action = timing_cfg.get("reaction_by_action")
    if isinstance(reaction_by_action, dict):
        action_cfg = reaction_by_action.get(action_type)
        if isinstance(action_cfg, dict):
            mean = float(action_cfg.get("mean", mean))
            stdev = float(action_cfg.get("stdev", stdev))
    delay = max(20.0, random.gauss(mean, stdev))
    return delay


def _get_client_bounds(snapshot):
    if not isinstance(snapshot, dict):
        return {}
    client = snapshot.get("client", {})
    if not isinstance(client, dict):
        return {}
    bounds = client.get("bounds", {})
    return bounds if isinstance(bounds, dict) else {}


def _snapshot_stale(snapshot) -> bool:
    if not isinstance(snapshot, dict):
        return True
    return bool(snapshot.get("stale", False))


def _prepare_ocr_regions(ocr_regions, frame):
    if not isinstance(ocr_regions, dict) or not isinstance(frame, dict):
        return ocr_regions
    image = frame.get("image")
    if image is None:
        return ocr_regions
    pil_image = None
    if hasattr(image, "save"):
        pil_image = image
    elif hasattr(image, "rgb") and hasattr(image, "size"):
        try:
            from PIL import Image
        except Exception:
            pil_image = None
        else:
            pil_image = Image.frombytes("RGB", image.size, image.rgb)
    if pil_image is None:
        return ocr_regions
    bounds = frame.get("bounds", {})
    offset_x = int(bounds.get("x", 0) or 0)
    offset_y = int(bounds.get("y", 0) or 0)
    prepared = {}
    for name, region in ocr_regions.items():
        if not isinstance(region, dict):
            continue
        prepared[name] = {
            "x": int(region.get("x", 0)) - offset_x,
            "y": int(region.get("y", 0)) - offset_y,
            "width": int(region.get("width", 0)),
            "height": int(region.get("height", 0)),
            "_image": pil_image,
        }
    return prepared


def _center_point(bounds):
    x = bounds.get("x", 0)
    y = bounds.get("y", 0)
    width = max(1, bounds.get("width", 1))
    height = max(1, bounds.get("height", 1))
    return int(x + width / 2), int(y + height / 2)


def _random_point(bounds, region="center"):
    x = bounds.get("x", 0)
    y = bounds.get("y", 0)
    width = max(1, bounds.get("width", 1))
    height = max(1, bounds.get("height", 1))
    if region == "top_right":
        px = x + int(width * random.uniform(0.72, 0.95))
        py = y + int(height * random.uniform(0.05, 0.25))
    elif region == "right_lower":
        px = x + int(width * random.uniform(0.75, 0.96))
        py = y + int(height * random.uniform(0.58, 0.92))
    else:
        px = x + int(width * random.uniform(0.2, 0.8))
        py = y + int(height * random.uniform(0.2, 0.8))
    return int(px), int(py)


def _ensure_payload(intent, key):
    if not isinstance(intent.payload, dict):
        intent.payload = {}
    section = intent.payload.get(key)
    if not isinstance(section, dict):
        section = {}
        intent.payload[key] = section
    return section


def _move_cursor(point, profile):
    motion = profile.get("motion", {}) if isinstance(profile, dict) else {}
    device = profile.get("device", {}) if isinstance(profile, dict) else {}
    noise = profile.get("input_noise", {}) if isinstance(profile, dict) else {}
    start = input_exec.get_cursor_pos()
    distance = ((point[0] - start[0]) ** 2 + (point[1] - start[1]) ** 2) ** 0.5
    steps = max(6, min(28, int(distance / 12)))
    curve = float(motion.get("curve_strength", 0.15))
    jitter_px = float(motion.get("micro_jitter_px", 0.0))
    step_delay_ms = float(device.get("polling_jitter_ms", 0.0)) + random.uniform(0.0, 3.0)
    if isinstance(noise, dict):
        frame_var_ms = noise.get("frame_time_variance_ms")
        if frame_var_ms is not None:
            try:
                step_delay_ms += float(frame_var_ms)
            except Exception:
                pass
    start_jitter_px = float(motion.get("start_jitter_px", jitter_px * 3.0))
    edge_margin_px = float(motion.get("edge_margin_px", 4.0))
    speed_ramp_mode = str(motion.get("speed_ramp_mode", "ease_in_out"))
    input_exec.move_mouse_path(
        int(point[0]),
        int(point[1]),
        steps=steps,
        curve_strength=curve,
        jitter_px=jitter_px,
        step_delay_ms=step_delay_ms,
        start_jitter_px=start_jitter_px,
        edge_margin_px=edge_margin_px,
        speed_ramp_mode=speed_ramp_mode,
    )


def _idle_profile_from_config(profile):
    idle_cfg = profile.get("idle", {}) if isinstance(profile, dict) else {}
    edge_pause_ms = idle_cfg.get("edge_pause_ms", (400, 1200))
    if isinstance(edge_pause_ms, (list, tuple)) and len(edge_pause_ms) == 2:
        edge_pause_ms = (int(edge_pause_ms[0]), int(edge_pause_ms[1]))
    else:
        edge_pause_ms = IdleBehaviorProfile().edge_pause_ms
    return IdleBehaviorProfile(
        idle_rate=float(idle_cfg.get("rate", IdleBehaviorProfile().idle_rate)),
        hover_weight=float(idle_cfg.get("hover_weight", IdleBehaviorProfile().hover_weight)),
        camera_glance_weight=float(idle_cfg.get("camera_glance_weight", IdleBehaviorProfile().camera_glance_weight)),
        inventory_check_weight=float(idle_cfg.get("inventory_check_weight", IdleBehaviorProfile().inventory_check_weight)),
        edge_pause_ms=edge_pause_ms,
    )


def _apply_focus_recovery(executor, snap, timing_payload):
    if not focus_recovery_needed(snap):
        return False
    bounds = _get_client_bounds(snap)
    if not bounds:
        return False
    cx, cy = _center_point(bounds)
    intent = build_focus_recovery_intent(cx, cy)
    intent.payload["snapshot"] = snap
    result = executor.execute(intent)
    if isinstance(timing_payload, dict):
        timing_payload.setdefault("focus_recovery", True)
    if isinstance(snap, dict):
        client = snap.get("client", {})
        if isinstance(client, dict):
            client["focused"] = True
    return result.success


def _apply_edge_pause(bounds, profile, timing_payload):
    if not bounds:
        return False
    idle_cfg = profile.get("idle", {}) if isinstance(profile, dict) else {}
    chance = float(idle_cfg.get("edge_pause_chance", 0.0))
    if chance <= 0 or random.random() >= chance:
        return False
    # Rest in place to avoid suspicious corner jumps.
    _ = input_exec.get_cursor_pos()
    pause_ms = random.uniform(IdleBehaviorProfile().edge_pause_ms[0], IdleBehaviorProfile().edge_pause_ms[1])
    if isinstance(idle_cfg.get("edge_pause_ms"), (list, tuple)) and len(idle_cfg.get("edge_pause_ms")) == 2:
        pause_ms = random.uniform(float(idle_cfg["edge_pause_ms"][0]), float(idle_cfg["edge_pause_ms"][1]))
    _sleep_ms(pause_ms)
    if isinstance(timing_payload, dict):
        timing_payload.setdefault("edge_pause_ms", float(pause_ms))
        timing_payload.setdefault("edge_pause_stationary", True)
    return True


def _apply_offscreen_travel(bounds, profile, timing_payload):
    if not bounds:
        return False
    idle_cfg = profile.get("idle", {}) if isinstance(profile, dict) else {}
    chance = float(idle_cfg.get("offscreen_travel_chance", 0.0))
    if chance <= 0 or random.random() >= chance:
        return False
    # Rest in place to avoid offscreen travel that looks suspicious.
    path = [input_exec.get_cursor_pos()]
    start_ts = time.time()
    for point in path:
        _move_cursor(point, profile)
    elapsed_ms = (time.time() - start_ts) * 1000.0
    if isinstance(timing_payload, dict):
        timing_payload.setdefault("offscreen_travel_ms", float(elapsed_ms))
        timing_payload.setdefault("offscreen_travel_stationary", True)
    return True


def _apply_viewport_scan(bounds, profile, timing_payload):
    if not bounds:
        return False
    idle_cfg = profile.get("idle", {}) if isinstance(profile, dict) else {}
    chance = float(idle_cfg.get("viewport_scan_chance", 0.0))
    if chance <= 0 or random.random() >= chance:
        return False
    points = scan_panel(bounds, rows=2, cols=3)
    start_ts = time.time()
    for point in points:
        _move_cursor(point, profile)
        pause_ms = random.uniform(40.0, 120.0)
        _sleep_ms(pause_ms)
    elapsed_ms = (time.time() - start_ts) * 1000.0
    if isinstance(timing_payload, dict):
        timing_payload.setdefault("viewport_scan_ms", float(elapsed_ms))
    return True


def _apply_idle_action(bounds, profile, timing_payload):
    if not bounds:
        return False
    idle_profile = _idle_profile_from_config(profile)
    if not should_idle_action(idle_profile):
        return False
    idle_cfg = profile.get("idle", {}) if isinstance(profile, dict) else {}
    action = choose_idle_action(idle_profile)
    if action == "hover":
        point = _random_point(bounds, "center")
        _move_cursor(point, profile)
        pause_cfg = idle_cfg.get("hover_pause_ms", (80, 240))
        pause_ms = random.uniform(float(pause_cfg[0]), float(pause_cfg[1])) if isinstance(pause_cfg, (list, tuple)) and len(pause_cfg) == 2 else 120.0
    elif action == "camera_glance":
        point = _random_point(bounds, "top_right")
        _move_cursor(point, profile)
        pause_cfg = idle_cfg.get("glance_pause_ms", (120, 320))
        pause_ms = random.uniform(float(pause_cfg[0]), float(pause_cfg[1])) if isinstance(pause_cfg, (list, tuple)) and len(pause_cfg) == 2 else 160.0
    else:
        point = _random_point(bounds, "right_lower")
        _move_cursor(point, profile)
        pause_cfg = idle_cfg.get("inventory_pause_ms", (120, 320))
        pause_ms = random.uniform(float(pause_cfg[0]), float(pause_cfg[1])) if isinstance(pause_cfg, (list, tuple)) and len(pause_cfg) == 2 else 180.0
    _sleep_ms(pause_ms)
    if isinstance(timing_payload, dict):
        timing_payload.setdefault("idle_action", action)
        timing_payload.setdefault("idle_pause_ms", float(pause_ms))
    return True


def _apply_tab_toggle(profile, timing_payload):
    idle_cfg = profile.get("idle", {}) if isinstance(profile, dict) else {}
    chance = float(idle_cfg.get("tab_toggle_chance", 0.0))
    if chance <= 0 or random.random() >= chance:
        return False
    keys = idle_cfg.get("tab_keys", [])
    if not isinstance(keys, list) or not keys:
        return False
    key = choose_tab_toggle([str(k) for k in keys])
    hold_ms = random.uniform(20.0, 60.0)
    input_exec.press_key_name(key, hold_ms=hold_ms)
    if isinstance(timing_payload, dict):
        timing_payload.setdefault("tab_toggle_key", key)
    return True


def _apply_idle_recovery(bounds, executor, snap, profile, timing_payload):
    if not bounds:
        return False
    idle_cfg = profile.get("idle", {}) if isinstance(profile, dict) else {}
    chance = float(idle_cfg.get("idle_recovery_chance", 0.0))
    if chance <= 0 or random.random() >= chance:
        return False
    start_ts = time.time()
    for step in idle_recovery_sequence():
        if step == "focus_recovery":
            _apply_focus_recovery(executor, snap, timing_payload)
        elif step == "ui_scan":
            _apply_viewport_scan(bounds, profile, timing_payload)
        elif step == "tab_inventory":
            _apply_tab_toggle(profile, timing_payload)
    elapsed_ms = (time.time() - start_ts) * 1000.0
    if isinstance(timing_payload, dict):
        timing_payload.setdefault("idle_recovery_ms", float(elapsed_ms))
    return True

def _load_action_policy(path: str) -> ActionPolicy:
    if not path:
        return ActionPolicy()
    policy_path = Path(path)
    if not policy_path.exists():
        return ActionPolicy()
    payload = load_json(policy_path, {})
    if not isinstance(payload, dict):
        return ActionPolicy()
    allowed = payload.get("allowed_actions")
    deny = payload.get("deny_actions")
    policy = ActionPolicy()
    if isinstance(allowed, list) and allowed:
        policy.allowed_actions = [str(item) for item in allowed]
    if isinstance(deny, list) and deny:
        policy.allowed_actions = [a for a in policy.allowed_actions if a not in deny]
    policy.cooldown_ms = int(payload.get("cooldown_ms", 0) or 0)
    policy.rate_limit_per_min = int(payload.get("rate_limit_per_min", 0) or 0)
    return policy


def _load_approval_policy(cfg: dict) -> ApprovalPolicy:
    policy = ApprovalPolicy()
    if not isinstance(cfg, dict):
        return policy
    approval_cfg = cfg.get("approval_policy", {})
    if not isinstance(approval_cfg, dict):
        return policy
    if "require_approval" in approval_cfg:
        policy.require_approval = bool(approval_cfg.get("require_approval", policy.require_approval))
    unsafe_actions = approval_cfg.get("unsafe_actions")
    if isinstance(unsafe_actions, list) and unsafe_actions:
        policy.unsafe_actions = [str(action) for action in unsafe_actions]
    auto_actions = approval_cfg.get("auto_approve_actions")
    if isinstance(auto_actions, list) and auto_actions:
        policy.auto_approve_actions = [str(action) for action in auto_actions]
    return policy


def _update_tutorial_state(state_path, decision_id, results):
    if not state_path:
        return
    state_file = Path(state_path)
    state = load_json(state_file, {})
    if not isinstance(state, dict):
        state = {}
    success_count = sum(1 for item in results if item.get("success"))
    failure_count = len(results) - success_count
    previous_id = state.get("last_decision_id", "")
    state["last_decision_id"] = decision_id or ""
    repeat_count = int(state.get("repeat_count", 0) or 0)
    if previous_id and previous_id == decision_id:
        repeat_count += 1
    else:
        repeat_count = 0
    state["repeat_count"] = repeat_count
    state["last_execution"] = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "decision_id": decision_id or "",
        "count": len(results),
        "success_count": success_count,
        "failure_count": failure_count,
        "results": results,
    }
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _resolve_retry(intent, profile):
    payload = intent.payload if isinstance(intent.payload, dict) else {}
    retry_cfg = payload.get("retry", {}) if isinstance(payload.get("retry"), dict) else {}
    profile_retry = profile.get("retry", {}) if isinstance(profile, dict) else {}
    max_attempts = int(
        retry_cfg.get(
            "max_attempts",
            payload.get("max_attempts", profile_retry.get("max_attempts", 1)),
        )
    )
    base_ms = int(
        retry_cfg.get(
            "backoff_base_ms",
            payload.get("backoff_base_ms", profile_retry.get("backoff_base_ms", 120)),
        )
    )
    max_ms = int(
        retry_cfg.get(
            "backoff_max_ms",
            payload.get("backoff_max_ms", profile_retry.get("backoff_max_ms", 800)),
        )
    )
    return max(1, max_attempts), base_ms, max_ms


def _execute_with_retry(executor, intent, profile):
    max_attempts, base_ms, max_ms = _resolve_retry(intent, profile)
    last_result = None
    base_target = None
    if isinstance(intent.target, dict) and "x" in intent.target and "y" in intent.target:
        base_target = (int(intent.target["x"]), int(intent.target["y"]))
    retry_cfg = intent.payload.get("retry", {}) if isinstance(intent.payload, dict) else {}
    reaim_px = float(retry_cfg.get("reaim_px", 3.0))
    for attempt in range(1, max_attempts + 1):
        result = executor.execute(intent)
        if not isinstance(result.details, dict):
            result.details = {}
        result.details["attempts"] = attempt
        last_result = result
        if result.success:
            return result
        if base_target and attempt < max_attempts and reaim_px > 0:
            jitter_x = random.uniform(-reaim_px, reaim_px)
            jitter_y = random.uniform(-reaim_px, reaim_px)
            intent.target["x"] = int(base_target[0] + jitter_x)
            intent.target["y"] = int(base_target[1] + jitter_y)
            if isinstance(intent.payload, dict):
                motion_payload = intent.payload.get("motion")
                if not isinstance(motion_payload, dict):
                    motion_payload = {}
                    intent.payload["motion"] = motion_payload
                motion_payload.setdefault("retry_reaim_px", float(reaim_px))
        if attempt < max_attempts:
            backoff_ms = default_backoff_ms(attempt, base_ms=base_ms, max_ms=max_ms)
            _sleep_ms(backoff_ms)
    return last_result


def _get_action_label(intent) -> str:
    if not isinstance(intent.payload, dict):
        payload_label = ""
    else:
        payload_label = intent.payload.get("action_label") or intent.payload.get("label") or ""
    if payload_label:
        return str(payload_label).lower()
    target = intent.target if isinstance(intent.target, dict) else {}
    target_label = target.get("label") or target.get("name") or ""
    return str(target_label).lower()


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


def _load_latest_kpi():
    log_path = ROOT / "logs" / "human_kpi.jsonl"
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            kpi = entry.get("kpi")
            if isinstance(kpi, dict):
                return kpi
    kpi_path = DATA_DIR / "human_kpi.json"
    if kpi_path.exists():
        payload = load_json(kpi_path, {})
        if isinstance(payload, dict) and payload:
            return payload
    return None


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
    kpi = _load_latest_kpi()
    if kpi:
        print("Human-likeness KPI")
        for key, val in kpi.items():
            print(f"- {key}: {val}")


def cmd_plan(state, model_message=None, prefer_model=False, snapshot_path=""):
    if model_message or prefer_model:
        if not model_message:
            model_message = "plan next step"
        cfg = load_config()
        snapshot = load_json(Path(snapshot_path), {}) if snapshot_path else None
        prompt = build_decision_prompt(state, model_message, snapshot=snapshot)
        payload, reply = _request_model_json(prompt, cfg)
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

    # Focus OSRS window before capture
    focus_window(window.handle, wait_ms=200)

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
    from src.ocr import run_ocr
    from src.ui_detector import detect_ui
    from src.minimap import infer_region

    snapshot = {
        "version": 1,
        "capture_id": f"cap_{uuid.uuid4().hex}",
        "timestamp": frame["timestamp"],
        "session_id": "local_capture",
        "stale": False,
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
        "chat": [],
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
        "ocr_metadata": {},
    }
    ocr_regions = load_json(DATA_DIR / "ocr_regions.json", {})
    if not ocr_regions:
        snapshot["stale"] = True
    ocr_config = load_json(DATA_DIR / "ocr_config.json", {})
    ocr_provider = "noop"
    if isinstance(ocr_config, dict):
        ocr_provider = str(ocr_config.get("provider", "noop") or "noop")
    ocr_regions = _prepare_ocr_regions(ocr_regions, frame)
    ocr_entries = run_ocr(ocr_regions, provider_name=ocr_provider, provider_config=ocr_config)
    if ocr_provider == "noop":
        snapshot["stale"] = True
    if isinstance(ocr_regions, dict) and ocr_regions:
        has_bounds = False
        for region in ocr_regions.values():
            if not isinstance(region, dict):
                continue
            if region.get("width", 0) or region.get("height", 0):
                has_bounds = True
                break
        if not has_bounds:
            snapshot["stale"] = True
    if not ocr_entries and ocr_provider != "noop":
        snapshot["stale"] = True
    snapshot["ocr"] = [
        {"region": entry.region, "text": entry.text, "confidence": entry.confidence}
        for entry in ocr_entries
    ]
    snapshot["ocr_metadata"]["provider"] = ocr_provider
    for entry in ocr_entries:
        if entry.region == "hover_text":
            snapshot["ui"]["hover_text"] = entry.text
        elif entry.region == "dialogue":
            snapshot["ui"]["dialogue_options"] = [line for line in entry.text.splitlines() if line.strip()]
        elif entry.region == "chat_box":
            snapshot["chat"] = [line for line in entry.text.splitlines() if line.strip()]
        elif entry.region == "inventory":
            items = [line.strip() for line in entry.text.splitlines() if line.strip()]
            snapshot["ocr_metadata"]["inventory_lines"] = items
        elif entry.region == "tooltips":
            snapshot["ocr_metadata"]["tooltips"] = [line.strip() for line in entry.text.splitlines() if line.strip()]
    if snapshot["ui"]["hover_text"]:
        snapshot["ui"]["cursor_state"] = "interact"
    chat_prompt = _chat_prompt_from_lines(snapshot.get("chat", []))
    if chat_prompt:
        snapshot["cues"]["chat_prompt"] = chat_prompt
    ui_regions = load_json(DATA_DIR / "ui_detector_regions.json", {})
    ui_elements = detect_ui(ui_regions)
    snapshot["ui"]["elements"] = [
        {
            "id": element.element_id,
            "type": element.element_type,
            "label": element.label,
            "state": element.state,
            "bounds": element.bounds,
        }
        for element in ui_elements
    ]
    snapshot["derived"]["location"] = infer_region(roi.get("minimap", {}))
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
    latest_path = SNAPSHOT_DIR / "snapshot_latest.json"
    latest_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"Captured snapshot to {out_path}")


def _load_chat_lines(path):
    if not path:
        return []
    chat_path = Path(path)
    if not chat_path.exists():
        print(f"Chat log not found: {path}")
        return []
    return [line.strip() for line in chat_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _chat_prompt_from_lines(lines):
    if not lines:
        return ""
    markers = ("click here to continue", "press space", "press space to continue", "space to continue")
    for line in lines:
        text = str(line).lower()
        if any(marker in text for marker in markers):
            return "continue"
    return ""


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


def _request_model_json(prompt, cfg):
    retries = cfg.get("strict_json_retries", 1)
    strict = cfg.get("strict_json", False)
    attempts = max(1, retries if strict else 1)
    last_reply = ""
    for _ in range(attempts):
        last_reply = run_local_model(prompt)
        payload = extract_json(last_reply)
        if payload is not None:
            return payload, last_reply
    return None, last_reply


def cmd_model_decision(state, message, snapshot_path=""):
    if not message:
        print("Message required. Use --message \"...\".")
        return
    snapshot = load_json(Path(snapshot_path), {}) if snapshot_path else None
    prompt = build_decision_prompt(state, message, snapshot=snapshot)
    cfg = load_config()
    payload, reply = _request_model_json(prompt, cfg)
    if payload is None:
        print("Model output is not valid JSON.")
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


def cmd_decision_view(path, limit):
    if not path:
        print("Trace path required. Use --trace-path <path>.")
        return
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue
        payload = entry.get("payload", {})
        stamp = entry.get("timestamp", "unknown")
        source = entry.get("source", "unknown")
        intent = payload.get("intent", "unknown")
        confidence = payload.get("confidence", "n/a")
        print(f"- {stamp} [{source}] {intent} (confidence {confidence})")


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


def cmd_decision_rotate(path, out_dir):
    if not path:
        print("Trace path required. Use --trace-path <path>.")
        return
    target_dir = Path(out_dir) if out_dir else (ROOT / "logs" / "archive")
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = target_dir / f"model_decisions_{stamp}.jsonl.gz"
    cmd_decision_export(path, str(out_path))
    Path(path).write_text("", encoding="utf-8")
    print(f"Rotated decision log to {out_path}")


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


def cmd_decision_consume(trace_path, execute=False, snapshot_path="", max_actions=0, seed=None):
    if not trace_path:
        print("Decision trace path required. Use --trace-path <path>.")
        return
    payload = latest_payload(Path(trace_path))
    if payload is None or not isinstance(payload, dict):
        print("No decision payload found.")
        return
    intents = build_action_intents(payload)
    if max_actions and max_actions > 0:
        intents = intents[:max_actions]
    decision_id = str(payload.get("decision_id", "")) if isinstance(payload, dict) else ""
    errors = validate_intents(intents)
    if errors:
        print("Action intent validation errors:")
        for err in errors:
            print(f"- {err}")
        return
    cues = {}
    snap = None
    if snapshot_path:
        snap = load_json(Path(snapshot_path), {})
        if isinstance(snap, dict):
            cues = snap.get("cues", {}) if isinstance(snap.get("cues"), dict) else {}
    if isinstance(snap, dict):
        chat_lines = snap.get("chat", [])
        if isinstance(chat_lines, list) and chat_lines:
            if not should_respond_to_chat([str(line) for line in chat_lines]):
                print("Chat suppressed: random event detected in snapshot.")
                return
    print("Decision intents (ready):")
    for intent in intents:
        print(f"- {intent.intent_id}: {intent.action_type} target={intent.target} confidence={intent.confidence}")
    if execute:
        executor = LiveExecutor()
        if execute == "dry-run":
            from src.actions import DryRunExecutor
            executor = DryRunExecutor()
        is_dry_run = execute == "dry-run"
        action_logger = ActionLogger()
        context_logger = ActionContextLogger()
        profile = get_active_profile() or {}
        cfg = load_config()
        safety_enabled = bool(cfg.get("safety_gates_enabled", False))
        policy = _load_action_policy(str(DATA_DIR / "action_policy.json"))
        rate_limiter = ActionRateLimiter(policy) if policy.rate_limit_per_min > 0 else None
        approval_policy = _load_approval_policy(cfg)
        timing_cfg = profile.get("timing_ms", {}) if isinstance(profile, dict) else {}
        session_cfg = profile.get("session", {}) if isinstance(profile, dict) else {}
        _maybe_seed_session(profile, seed)
        confidence_cfg = profile.get("confidence_gate", {}) if isinstance(profile, dict) else {}
        confidence_threshold = float(confidence_cfg.get("threshold", 0.6))
        interrupt_cfg = profile.get("interrupts", {}) if isinstance(profile, dict) else {}
        interrupt_enabled = True
        if isinstance(interrupt_cfg, dict) and "enabled" in interrupt_cfg:
            interrupt_enabled = bool(interrupt_cfg.get("enabled", True))
        base_ms = float(timing_cfg.get("reaction_mean", 180)) * 0.5
        burst_mean = max(1, int(session_cfg.get("burst_mean_actions", 10)))
        rest_mean_ms = float(session_cfg.get("rest_mean_ms", 0))
        burst_count = 0
        results = []
        last_action_ts = time.time()
        consecutive_failures = 0
        periodic_every = 5
        variability = float(session_cfg.get("action_order_variability", 0.2))
        intents = vary_action_order(intents, variability_rate=variability)
        for idx, intent in enumerate(intents):
            if _escape_pressed():
                print("Escape pressed. Aborting execution.")
                break
            if isinstance(intent.payload, dict) and isinstance(snap, dict):
                intent.payload.setdefault("snapshot", snap)
            snap_before = snap
            timing_payload = _ensure_payload(intent, "timing")
            if snapshot_path and interrupt_enabled:
                pause_ms = apply_interrupt_pause(snap, profile, sleep_fn=time.sleep)
                if pause_ms and isinstance(intent.payload, dict):
                    timing_payload.setdefault("interrupt_pause_ms", float(pause_ms))
            if snapshot_path and isinstance(snap, dict) and not is_dry_run:
                chat_lines = snap.get("chat", [])
                if isinstance(chat_lines, list) and chat_lines:
                    if should_panic_on_chat([str(line) for line in chat_lines], InterruptProfile()):
                        panic_ms = random.uniform(300.0, 800.0)
                        _sleep_ms(panic_ms)
                        timing_payload.setdefault("panic_pause_ms", float(panic_ms))
                        result = ActionResult(
                            intent_id=intent.intent_id,
                            success=False,
                            failure_reason="panic_chat",
                        )
                        action_logger.log(intent, result)
                        print(f"Skipped {intent.intent_id}: {result.failure_reason}")
                        results.append(
                            {"intent_id": intent.intent_id, "success": False, "failure_reason": result.failure_reason}
                        )
                        continue
            if snapshot_path and isinstance(snap, dict):
                bounds = _get_client_bounds(snap)
                if focus_recovery_needed(snap):
                    _apply_focus_recovery(executor, snap, timing_payload)
                idle_cfg = profile.get("idle", {}) if isinstance(profile, dict) else {}
                idle_after_s = float(idle_cfg.get("idle_recovery_after_s", 0.0)) if isinstance(idle_cfg, dict) else 0.0
                if idle_after_s and (time.time() - last_action_ts) >= idle_after_s:
                    _apply_idle_recovery(bounds, executor, snap, profile, timing_payload)
                _apply_edge_pause(bounds, profile, timing_payload)
                _apply_offscreen_travel(bounds, profile, timing_payload)
                did_idle = _apply_idle_action(bounds, profile, timing_payload)
                if did_idle:
                    _apply_tab_toggle(profile, timing_payload)
                if intent.action_type == "click":
                    _apply_viewport_scan(bounds, profile, timing_payload)
            drift_dx, drift_dy = sample_attention_drift_offset(profile, idx)
            if drift_dx or drift_dy:
                if isinstance(intent.payload, dict):
                    motion_payload = intent.payload.get("motion")
                    if not isinstance(motion_payload, dict):
                        motion_payload = {}
                        intent.payload["motion"] = motion_payload
                    motion_payload.setdefault("attention_drift_dx", float(drift_dx))
                    motion_payload.setdefault("attention_drift_dy", float(drift_dy))
                if isinstance(intent.target, dict) and "x" in intent.target and "y" in intent.target:
                    intent.target["x"] = int(intent.target["x"] + drift_dx)
                    intent.target["y"] = int(intent.target["y"] + drift_dy)
            precheck_errors = pre_action_gate(intent, snap if snapshot_path else None)
            if precheck_errors:
                result = ActionResult(
                    intent_id=intent.intent_id,
                    success=False,
                    failure_reason="precheck_failed",
                    details={"errors": precheck_errors},
                )
                action_logger.log(intent, result)
                print(f"Skipped {intent.intent_id}: {result.failure_reason} {precheck_errors}")
                results.append(
                    {"intent_id": intent.intent_id, "success": False, "failure_reason": result.failure_reason}
                )
                continue
            reaction_ms = _sample_reaction_delay(profile, intent.action_type)
            if reaction_ms:
                _sleep_ms(reaction_ms)
                timing_payload.setdefault("reaction_ms", float(reaction_ms))
            low_confidence = requires_confidence_gate(intent, threshold=confidence_threshold)
            if low_confidence:
                pause_ms = random.uniform(80.0, 180.0)
                _sleep_ms(pause_ms)
                if isinstance(intent.payload, dict):
                    timing_payload = intent.payload.get("timing")
                    if not isinstance(timing_payload, dict):
                        timing_payload = {}
                        intent.payload["timing"] = timing_payload
                    timing_payload.setdefault("confidence_pause_ms", float(pause_ms))
            if snapshot_path:
                snap_check = load_json(Path(snapshot_path), {})
                if isinstance(snap_check, dict):
                    hover_text = snap_check.get("ui", {}).get("hover_text", "")
                    if intent.action_type == "click" and not hover_text and not _snapshot_stale(snap_check):
                        result = ActionResult(
                            intent_id=intent.intent_id,
                            success=False,
                            failure_reason="low_confidence_hover_missing",
                            details={"threshold": confidence_threshold, "hover_text": hover_text},
                        )
                        action_logger.log(intent, result)
                        print(f"Skipped {intent.intent_id}: {result.failure_reason}")
                        results.append(
                            {"intent_id": intent.intent_id, "success": False, "failure_reason": result.failure_reason}
                        )
                        continue
                    snap = snap_check
            if intent.action_type == "click" and snapshot_path:
                hover_check_chance = float(
                    intent.payload.get("hover_check_chance", 0.6) if isinstance(intent.payload, dict) else 0.6
                )
                if low_confidence:
                    hover_check_chance = 1.0
                if should_check_hover_text(hover_check_chance):
                    hover_pause_ms = random.uniform(60.0, 140.0)
                    _sleep_ms(hover_pause_ms)
                    snap_check = load_json(Path(snapshot_path), {})
                    hover_text = ""
                    if isinstance(snap_check, dict):
                        hover_text = snap_check.get("ui", {}).get("hover_text", "")
                        snap = snap_check
                    if isinstance(intent.payload, dict):
                        timing_payload = intent.payload.get("timing")
                        if not isinstance(timing_payload, dict):
                            timing_payload = {}
                            intent.payload["timing"] = timing_payload
                        timing_payload.setdefault("hover_check_pause_ms", float(hover_pause_ms))
                    if not hover_text and not _snapshot_stale(snap_check):
                        result = ActionResult(
                            intent_id=intent.intent_id,
                            success=False,
                              failure_reason="hover_check_missing",
                              details={"hover_text": hover_text},
                        )
                        action_logger.log(intent, result)
                        print(f"Skipped {intent.intent_id}: {result.failure_reason}")
                        results.append(
                            {"intent_id": intent.intent_id, "success": False, "failure_reason": result.failure_reason}
                        )
                        continue
            if snapshot_path and isinstance(intent.payload, dict):
                element_id = intent.payload.get("element_id")
                if element_id and isinstance(snap, dict) and should_wait_for_occlusion(snap, str(element_id)):
                    wait_ms = random.uniform(140.0, 320.0)
                    _sleep_ms(wait_ms)
                    timing_payload = intent.payload.get("timing")
                    if not isinstance(timing_payload, dict):
                        timing_payload = {}
                        intent.payload["timing"] = timing_payload
                    timing_payload.setdefault("occlusion_wait_ms", float(wait_ms))
                    snap_check = load_json(Path(snapshot_path), {})
                    if isinstance(snap_check, dict) and should_wait_for_occlusion(snap_check, str(element_id)):
                        reason = occlusion_reason(snap_check, str(element_id)) or "occluded"
                        result = ActionResult(
                            intent_id=intent.intent_id,
                            success=False,
                            failure_reason="occluded",
                            details={"reason": reason},
                        )
                        action_logger.log(intent, result)
                        print(f"Skipped {intent.intent_id}: occluded ({reason})")
                        results.append(
                            {"intent_id": intent.intent_id, "success": False, "failure_reason": result.failure_reason}
                        )
                        continue
                    snap = snap_check
            if intent.action_type in {"click", "move"} and snapshot_path:
                prev_bounds = {}
                cur_bounds = {}
                if isinstance(snap_before, dict):
                    prev_bounds = snap_before.get("client", {}).get("bounds", {}) if isinstance(
                        snap_before.get("client", {}), dict
                    ) else {}
                snap_check = load_json(Path(snapshot_path), {})
                if isinstance(snap_check, dict):
                    cur_bounds = snap_check.get("client", {}).get("bounds", {}) if isinstance(
                        snap_check.get("client", {}), dict
                    ) else {}
                    snap = snap_check
                if prev_bounds and cur_bounds and isinstance(intent.target, dict) and "x" in intent.target and "y" in intent.target:
                    new_point, shifted = reaim_if_shifted(prev_bounds, cur_bounds, (intent.target["x"], intent.target["y"]))
                    if shifted:
                        intent.target["x"] = int(new_point[0])
                        intent.target["y"] = int(new_point[1])
                        if isinstance(intent.payload, dict):
                            motion_payload = intent.payload.get("motion")
                            if not isinstance(motion_payload, dict):
                                motion_payload = {}
                                intent.payload["motion"] = motion_payload
                            motion_payload.setdefault("reaim_shifted", True)
            action_label = _get_action_label(intent)
            if action_label and should_confirm_irreversible(action_label):
                pause_ms = random.uniform(120.0, 260.0)
                _sleep_ms(pause_ms)
                if isinstance(intent.payload, dict):
                    timing_payload = intent.payload.get("timing")
                    if not isinstance(timing_payload, dict):
                        timing_payload = {}
                        intent.payload["timing"] = timing_payload
                    timing_payload.setdefault("double_check_pause_ms", float(pause_ms))
                if snapshot_path:
                    snap_check = load_json(Path(snapshot_path), {})
                    if isinstance(snap_check, dict):
                        hover_text = snap_check.get("ui", {}).get("hover_text", "")
                        if hover_text and action_label not in hover_text.lower():
                            result = ActionResult(
                                intent_id=intent.intent_id,
                                success=False,
                                failure_reason="double_check_hover_mismatch",
                                details={"label": action_label},
                            )
                            action_logger.log(intent, result)
                            print(f"Skipped {intent.intent_id}: {result.failure_reason}")
                            results.append(
                                {"intent_id": intent.intent_id, "success": False, "failure_reason": result.failure_reason}
                            )
                            continue
            if not is_dry_run and requires_approval(intent, approval_policy):
                result = ActionResult(
                    intent_id=intent.intent_id,
                    success=False,
                    failure_reason="approval_required",
                    details={"policy": "data/local_model.json"},
                )
            elif safety_enabled and policy_check(intent, policy):
                result = ActionResult(
                    intent_id=intent.intent_id,
                    success=False,
                    failure_reason="policy_block",
                    details={"policy": "data/action_policy.json"},
                )
            elif safety_enabled and rate_limiter is not None and not rate_limiter.allow(time.time()):
                result = ActionResult(
                    intent_id=intent.intent_id,
                    success=False,
                    failure_reason="rate_limited",
                    details={"rate_limit_per_min": policy.rate_limit_per_min},
                )
            else:
                result = _execute_with_retry(executor, intent, profile)
            ui_changes = []
            if snapshot_path:
                snap_after = load_json(Path(snapshot_path), {})
                if isinstance(snap_after, dict):
                    ui_changes = detect_ui_change(snap_before, snap_after)
                    snap = snap_after
            if ui_changes:
                pause_ms = random.uniform(120.0, 320.0)
                _sleep_ms(pause_ms)
                if isinstance(intent.payload, dict):
                    timing_payload = intent.payload.get("timing")
                    if not isinstance(timing_payload, dict):
                        timing_payload = {}
                        intent.payload["timing"] = timing_payload
                    timing_payload.setdefault("ui_change_pause_ms", float(pause_ms))
                result.details["ui_changes"] = ui_changes
                result.details["abort_after"] = True
            action_logger.log(intent, result)
            timing = intent.payload.get("timing") if isinstance(intent.payload, dict) else None
            motion = intent.payload.get("motion") if isinstance(intent.payload, dict) else None
            if isinstance(timing, dict) or isinstance(motion, dict):
                log_action_context(
                    intent.intent_id,
                    decision_id,
                    timing if isinstance(timing, dict) else {},
                    motion if isinstance(motion, dict) else {},
                    context_logger,
                )
            delay_ms = 0
            if isinstance(intent.payload, dict):
                delay_ms = int(intent.payload.get("delay_ms", 0) or 0)
            if delay_ms > 0:
                time.sleep(delay_ms / 1000.0)
            cooldown_ms = 0
            if isinstance(intent.payload, dict):
                cooldown_ms = int(intent.payload.get("cooldown_ms", 0) or 0)
            if not cooldown_ms:
                cooldown_ms = int(session_cfg.get("cooldown_ms", 0) or 0)
            _sleep_ms(cooldown_ms)
            print(f"Executed {intent.intent_id}: {result.success} {result.failure_reason}")
            results.append(
                {"intent_id": intent.intent_id, "success": result.success, "failure_reason": result.failure_reason}
            )
            if not is_dry_run and snapshot_path and isinstance(snap, dict) and periodic_every > 0:
                if (idx + 1) % periodic_every == 0:
                    bounds = _client_bounds_tuple(snap)
                    if bounds:
                        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                        log_dir = ROOT / "logs"
                        log_dir.mkdir(exist_ok=True)
                        save_frame(bounds, str(log_dir / f"periodic_{stamp}_{idx+1}.png"))
            if not result.success:
                consecutive_failures += 1
            else:
                consecutive_failures = 0
            if consecutive_failures >= 2:
                _capture_stuck_artifacts(snap, intent.intent_id, result.failure_reason)
                consecutive_failures = 0
            if ui_changes:
                print(f"Aborting after {intent.intent_id}: ui changed {ui_changes}")
                break
            burst_count += 1
            if idx == len(intents) - 1:
                continue
            drift_ms = sample_fatigue_drift_ms(profile, idx)
            if drift_ms:
                _sleep_ms(drift_ms)
                if isinstance(intent.payload, dict):
                    timing_payload = intent.payload.get("timing")
                    if not isinstance(timing_payload, dict):
                        timing_payload = {}
                        intent.payload["timing"] = timing_payload
                    timing_payload.setdefault("fatigue_drift_ms", float(drift_ms))
            spacing_ms = apply_spacing_delay(base_ms, cues, context="simple")
            jitter = random.uniform(-0.1, 0.25) * base_ms
            spacing_ms = max(30.0, spacing_ms + jitter)
            if rest_mean_ms and burst_count >= burst_mean:
                burst_rest_ms = sample_burst_rest_ms(profile) or random.uniform(0.6, 1.4) * rest_mean_ms
                spacing_ms += burst_rest_ms
                burst_count = 0
            time.sleep(spacing_ms / 1000.0)
        _write_execution_summary(results)


def cmd_decision_execute_file(path, dry_run=False, snapshot_path="", max_actions=0, seed=None):
    if not path:
        print("Decision file path required. Use --model-output <path>.")
        return []
    payload = load_decision_file(Path(path))
    if payload is None:
        print("Decision file is missing or invalid JSON.")
        return []
    intents = build_action_intents(payload)
    if max_actions and max_actions > 0:
        intents = intents[:max_actions]
    decision_id = str(payload.get("decision_id", "")) if isinstance(payload, dict) else ""
    errors = validate_intents(intents)
    if errors:
        print("Action intent validation errors:")
        for err in errors:
            print(f"- {err}")
        return []
    executor = LiveExecutor()
    if dry_run:
        from src.actions import DryRunExecutor
        executor = DryRunExecutor()
    is_dry_run = dry_run
    action_logger = ActionLogger()
    context_logger = ActionContextLogger()
    cues = {}
    snap = None
    if snapshot_path:
        snap = load_json(Path(snapshot_path), {})
        if isinstance(snap, dict):
            cues = snap.get("cues", {}) if isinstance(snap.get("cues"), dict) else {}
    if isinstance(snap, dict):
        chat_lines = snap.get("chat", [])
        if isinstance(chat_lines, list) and chat_lines:
            if not should_respond_to_chat([str(line) for line in chat_lines]):
                print("Chat suppressed: random event detected in snapshot.")
                return []
    profile = get_active_profile() or {}
    cfg = load_config()
    safety_enabled = bool(cfg.get("safety_gates_enabled", False))
    policy = _load_action_policy(str(DATA_DIR / "action_policy.json"))
    rate_limiter = ActionRateLimiter(policy) if policy.rate_limit_per_min > 0 else None
    approval_policy = _load_approval_policy(cfg)
    timing_cfg = profile.get("timing_ms", {}) if isinstance(profile, dict) else {}
    session_cfg = profile.get("session", {}) if isinstance(profile, dict) else {}
    _maybe_seed_session(profile, seed)
    confidence_cfg = profile.get("confidence_gate", {}) if isinstance(profile, dict) else {}
    confidence_threshold = float(confidence_cfg.get("threshold", 0.6))
    interrupt_cfg = profile.get("interrupts", {}) if isinstance(profile, dict) else {}
    interrupt_enabled = True
    if isinstance(interrupt_cfg, dict) and "enabled" in interrupt_cfg:
        interrupt_enabled = bool(interrupt_cfg.get("enabled", True))
    base_ms = float(timing_cfg.get("reaction_mean", 180)) * 0.5
    burst_mean = max(1, int(session_cfg.get("burst_mean_actions", 10)))
    rest_mean_ms = float(session_cfg.get("rest_mean_ms", 0))
    burst_count = 0
    results = []
    last_action_ts = time.time()
    consecutive_failures = 0
    periodic_every = 5
    variability = float(session_cfg.get("action_order_variability", 0.2))
    intents = vary_action_order(intents, variability_rate=variability)
    for idx, intent in enumerate(intents):
        if _escape_pressed():
            print("Escape pressed. Aborting execution.")
            break
        if isinstance(intent.payload, dict) and isinstance(snap, dict):
            intent.payload.setdefault("snapshot", snap)
        snap_before = snap
        timing_payload = _ensure_payload(intent, "timing")
        if snapshot_path and interrupt_enabled:
            pause_ms = apply_interrupt_pause(snap, profile, sleep_fn=time.sleep)
            if pause_ms and isinstance(intent.payload, dict):
                timing_payload.setdefault("interrupt_pause_ms", float(pause_ms))
        if snapshot_path and isinstance(snap, dict) and not is_dry_run:
            chat_lines = snap.get("chat", [])
            if isinstance(chat_lines, list) and chat_lines:
                if should_panic_on_chat([str(line) for line in chat_lines], InterruptProfile()):
                    panic_ms = random.uniform(300.0, 800.0)
                    _sleep_ms(panic_ms)
                    timing_payload.setdefault("panic_pause_ms", float(panic_ms))
                    result = ActionResult(
                        intent_id=intent.intent_id,
                        success=False,
                        failure_reason="panic_chat",
                    )
                    action_logger.log(intent, result)
                    print(f"Skipped {intent.intent_id}: {result.failure_reason}")
                    results.append(
                        {"intent_id": intent.intent_id, "success": False, "failure_reason": result.failure_reason}
                    )
                    continue
        if snapshot_path and isinstance(snap, dict):
            bounds = _get_client_bounds(snap)
            if focus_recovery_needed(snap):
                _apply_focus_recovery(executor, snap, timing_payload)
            idle_cfg = profile.get("idle", {}) if isinstance(profile, dict) else {}
            idle_after_s = float(idle_cfg.get("idle_recovery_after_s", 0.0)) if isinstance(idle_cfg, dict) else 0.0
            if idle_after_s and (time.time() - last_action_ts) >= idle_after_s:
                _apply_idle_recovery(bounds, executor, snap, profile, timing_payload)
            _apply_edge_pause(bounds, profile, timing_payload)
            _apply_offscreen_travel(bounds, profile, timing_payload)
            did_idle = _apply_idle_action(bounds, profile, timing_payload)
            if did_idle:
                _apply_tab_toggle(profile, timing_payload)
            if intent.action_type == "click":
                _apply_viewport_scan(bounds, profile, timing_payload)
        drift_dx, drift_dy = sample_attention_drift_offset(profile, idx)
        if drift_dx or drift_dy:
            if isinstance(intent.payload, dict):
                motion_payload = intent.payload.get("motion")
                if not isinstance(motion_payload, dict):
                    motion_payload = {}
                    intent.payload["motion"] = motion_payload
                motion_payload.setdefault("attention_drift_dx", float(drift_dx))
                motion_payload.setdefault("attention_drift_dy", float(drift_dy))
            if isinstance(intent.target, dict) and "x" in intent.target and "y" in intent.target:
                intent.target["x"] = int(intent.target["x"] + drift_dx)
                intent.target["y"] = int(intent.target["y"] + drift_dy)
        precheck_errors = pre_action_gate(intent, snap if snapshot_path else None)
        if precheck_errors:
            result = ActionResult(
                intent_id=intent.intent_id,
                success=False,
                failure_reason="precheck_failed",
                details={"errors": precheck_errors},
            )
            action_logger.log(intent, result)
            print(f"Skipped {intent.intent_id}: {result.failure_reason} {precheck_errors}")
            results.append(
                {"intent_id": intent.intent_id, "success": False, "failure_reason": result.failure_reason}
            )
            continue
        reaction_ms = _sample_reaction_delay(profile, intent.action_type)
        if reaction_ms:
            _sleep_ms(reaction_ms)
            timing_payload.setdefault("reaction_ms", float(reaction_ms))
        low_confidence = requires_confidence_gate(intent, threshold=confidence_threshold)
        if low_confidence:
            pause_ms = random.uniform(80.0, 180.0)
            _sleep_ms(pause_ms)
            if isinstance(intent.payload, dict):
                timing_payload = intent.payload.get("timing")
                if not isinstance(timing_payload, dict):
                    timing_payload = {}
                    intent.payload["timing"] = timing_payload
                timing_payload.setdefault("confidence_pause_ms", float(pause_ms))
            if snapshot_path:
                snap_check = load_json(Path(snapshot_path), {})
                if isinstance(snap_check, dict):
                    hover_text = snap_check.get("ui", {}).get("hover_text", "")
                    if intent.action_type == "click" and not hover_text and not _snapshot_stale(snap_check):
                        result = ActionResult(
                            intent_id=intent.intent_id,
                            success=False,
                            failure_reason="low_confidence_hover_missing",
                    details={"threshold": confidence_threshold, "hover_text": hover_text},
                        )
                        action_logger.log(intent, result)
                        print(f"Skipped {intent.intent_id}: {result.failure_reason}")
                        results.append(
                            {"intent_id": intent.intent_id, "success": False, "failure_reason": result.failure_reason}
                        )
                        continue
                    snap = snap_check
        if intent.action_type == "click" and snapshot_path:
            hover_check_chance = float(
                intent.payload.get("hover_check_chance", 0.6) if isinstance(intent.payload, dict) else 0.6
            )
            if low_confidence:
                hover_check_chance = 1.0
            if should_check_hover_text(hover_check_chance):
                hover_pause_ms = random.uniform(60.0, 140.0)
                _sleep_ms(hover_pause_ms)
                snap_check = load_json(Path(snapshot_path), {})
                hover_text = ""
                if isinstance(snap_check, dict):
                    hover_text = snap_check.get("ui", {}).get("hover_text", "")
                    snap = snap_check
                if isinstance(intent.payload, dict):
                    timing_payload = intent.payload.get("timing")
                    if not isinstance(timing_payload, dict):
                        timing_payload = {}
                        intent.payload["timing"] = timing_payload
                    timing_payload.setdefault("hover_check_pause_ms", float(hover_pause_ms))
                if not hover_text and not _snapshot_stale(snap_check):
                    result = ActionResult(
                        intent_id=intent.intent_id,
                        success=False,
                    failure_reason="hover_check_missing",
                    details={"hover_text": hover_text},
                    )
                    action_logger.log(intent, result)
                    print(f"Skipped {intent.intent_id}: {result.failure_reason}")
                    results.append(
                        {"intent_id": intent.intent_id, "success": False, "failure_reason": result.failure_reason}
                    )
                    continue
        if snapshot_path and isinstance(intent.payload, dict):
            element_id = intent.payload.get("element_id")
            if element_id and isinstance(snap, dict) and should_wait_for_occlusion(snap, str(element_id)):
                wait_ms = random.uniform(140.0, 320.0)
                _sleep_ms(wait_ms)
                timing_payload = intent.payload.get("timing")
                if not isinstance(timing_payload, dict):
                    timing_payload = {}
                    intent.payload["timing"] = timing_payload
                timing_payload.setdefault("occlusion_wait_ms", float(wait_ms))
                snap_check = load_json(Path(snapshot_path), {})
                if isinstance(snap_check, dict) and should_wait_for_occlusion(snap_check, str(element_id)):
                    reason = occlusion_reason(snap_check, str(element_id)) or "occluded"
                    result = ActionResult(
                        intent_id=intent.intent_id,
                        success=False,
                        failure_reason="occluded",
                        details={"reason": reason},
                    )
                    action_logger.log(intent, result)
                    print(f"Skipped {intent.intent_id}: occluded ({reason})")
                    results.append(
                        {"intent_id": intent.intent_id, "success": False, "failure_reason": result.failure_reason}
                    )
                    continue
                snap = snap_check
        if intent.action_type in {"click", "move"} and snapshot_path:
            prev_bounds = {}
            cur_bounds = {}
            if isinstance(snap_before, dict):
                prev_bounds = snap_before.get("client", {}).get("bounds", {}) if isinstance(
                    snap_before.get("client", {}), dict
                ) else {}
            snap_check = load_json(Path(snapshot_path), {})
            if isinstance(snap_check, dict):
                cur_bounds = snap_check.get("client", {}).get("bounds", {}) if isinstance(
                    snap_check.get("client", {}), dict
                ) else {}
                snap = snap_check
            if prev_bounds and cur_bounds and isinstance(intent.target, dict) and "x" in intent.target and "y" in intent.target:
                new_point, shifted = reaim_if_shifted(prev_bounds, cur_bounds, (intent.target["x"], intent.target["y"]))
                if shifted:
                    intent.target["x"] = int(new_point[0])
                    intent.target["y"] = int(new_point[1])
                    if isinstance(intent.payload, dict):
                        motion_payload = intent.payload.get("motion")
                        if not isinstance(motion_payload, dict):
                            motion_payload = {}
                            intent.payload["motion"] = motion_payload
                        motion_payload.setdefault("reaim_shifted", True)
        action_label = _get_action_label(intent)
        if action_label and should_confirm_irreversible(action_label):
            pause_ms = random.uniform(120.0, 260.0)
            _sleep_ms(pause_ms)
            if isinstance(intent.payload, dict):
                timing_payload = intent.payload.get("timing")
                if not isinstance(timing_payload, dict):
                    timing_payload = {}
                    intent.payload["timing"] = timing_payload
                timing_payload.setdefault("double_check_pause_ms", float(pause_ms))
            if snapshot_path:
                snap_check = load_json(Path(snapshot_path), {})
                if isinstance(snap_check, dict):
                    hover_text = snap_check.get("ui", {}).get("hover_text", "")
                    if hover_text and action_label not in hover_text.lower():
                        result = ActionResult(
                            intent_id=intent.intent_id,
                            success=False,
                            failure_reason="double_check_hover_mismatch",
                            details={"label": action_label},
                        )
                        action_logger.log(intent, result)
                        print(f"Skipped {intent.intent_id}: {result.failure_reason}")
                        results.append(
                            {"intent_id": intent.intent_id, "success": False, "failure_reason": result.failure_reason}
                        )
                        continue
        if not is_dry_run and requires_approval(intent, approval_policy):
            result = ActionResult(
                intent_id=intent.intent_id,
                success=False,
                failure_reason="approval_required",
                details={"policy": "data/local_model.json"},
            )
        elif safety_enabled and policy_check(intent, policy):
            result = ActionResult(
                intent_id=intent.intent_id,
                success=False,
                failure_reason="policy_block",
                details={"policy": "data/action_policy.json"},
            )
        elif safety_enabled and rate_limiter is not None and not rate_limiter.allow(time.time()):
            result = ActionResult(
                intent_id=intent.intent_id,
                success=False,
                failure_reason="rate_limited",
                details={"rate_limit_per_min": policy.rate_limit_per_min},
            )
        else:
            result = _execute_with_retry(executor, intent, profile)
        ui_changes = []
        if snapshot_path:
            snap_after = load_json(Path(snapshot_path), {})
            if isinstance(snap_after, dict):
                ui_changes = detect_ui_change(snap_before, snap_after)
                snap = snap_after
        if ui_changes:
            pause_ms = random.uniform(120.0, 320.0)
            _sleep_ms(pause_ms)
            if isinstance(intent.payload, dict):
                timing_payload = intent.payload.get("timing")
                if not isinstance(timing_payload, dict):
                    timing_payload = {}
                    intent.payload["timing"] = timing_payload
                timing_payload.setdefault("ui_change_pause_ms", float(pause_ms))
            result.details["ui_changes"] = ui_changes
            result.details["abort_after"] = True
        action_logger.log(intent, result)
        timing = intent.payload.get("timing") if isinstance(intent.payload, dict) else None
        motion = intent.payload.get("motion") if isinstance(intent.payload, dict) else None
        if isinstance(timing, dict) or isinstance(motion, dict):
            log_action_context(
                intent.intent_id,
                decision_id,
                timing if isinstance(timing, dict) else {},
                motion if isinstance(motion, dict) else {},
                context_logger,
            )
        delay_ms = 0
        if isinstance(intent.payload, dict):
            delay_ms = int(intent.payload.get("delay_ms", 0) or 0)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
        cooldown_ms = 0
        if isinstance(intent.payload, dict):
            cooldown_ms = int(intent.payload.get("cooldown_ms", 0) or 0)
        if not cooldown_ms:
            cooldown_ms = int(session_cfg.get("cooldown_ms", 0) or 0)
        _sleep_ms(cooldown_ms)
        print(f"Executed {intent.intent_id}: {result.success} {result.failure_reason}")
        if not is_dry_run and snapshot_path and isinstance(snap, dict) and periodic_every > 0:
            if (idx + 1) % periodic_every == 0:
                bounds = _client_bounds_tuple(snap)
                if bounds:
                    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    log_dir = ROOT / "logs"
                    log_dir.mkdir(exist_ok=True)
                    save_frame(bounds, str(log_dir / f"periodic_{stamp}_{idx+1}.png"))
        if not result.success:
            consecutive_failures += 1
        else:
            consecutive_failures = 0
        if consecutive_failures >= 2:
            _capture_stuck_artifacts(snap, intent.intent_id, result.failure_reason)
            consecutive_failures = 0
        last_action_ts = time.time()
        burst_count += 1
        if idx != len(intents) - 1:
            drift_ms = sample_fatigue_drift_ms(profile, idx)
            if drift_ms:
                _sleep_ms(drift_ms)
                if isinstance(intent.payload, dict):
                    timing_payload = intent.payload.get("timing")
                    if not isinstance(timing_payload, dict):
                        timing_payload = {}
                        intent.payload["timing"] = timing_payload
                    timing_payload.setdefault("fatigue_drift_ms", float(drift_ms))
            spacing_ms = apply_spacing_delay(base_ms, cues, context="simple")
            jitter = random.uniform(-0.1, 0.25) * base_ms
            spacing_ms = max(30.0, spacing_ms + jitter)
            if rest_mean_ms and burst_count >= burst_mean:
                burst_rest_ms = sample_burst_rest_ms(profile) or random.uniform(0.6, 1.4) * rest_mean_ms
                spacing_ms += burst_rest_ms
                burst_count = 0
            time.sleep(spacing_ms / 1000.0)
        results.append(
            {"intent_id": intent.intent_id, "success": result.success, "failure_reason": result.failure_reason}
        )
        if ui_changes:
            print(f"Aborting after {intent.intent_id}: ui changed {ui_changes}")
            break
    _write_execution_summary(results)
    return results


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
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--kpi", default="")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-actions", type=int, default=0)
    parser.add_argument("--sleep-ms", type=int, default=0)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--tutorial-state", default=str(DATA_DIR / "tutorial_island_state.json"))
    parser.add_argument("--tutorial-decisions", default=str(DATA_DIR / "tutorial_island_decisions.json"))
    args = parser.parse_args()
    if not args.roi:
        default_roi = DATA_DIR / "roi.json"
        if default_roi.exists():
            args.roi = str(default_roi)

    cmd = args.command.lower()
    if cmd == "tutorial-loop":
        run_tutorial_loop(args.snapshot, args.tutorial_state, args.tutorial_decisions, args.out)
        return
    if cmd == "go":
        profile = get_active_profile()
        if not profile:
            print("Active profile not set. Use profile-select before running go.")
            return
        _maybe_seed_session(profile, args.seed)
        snapshot_path = args.snapshot or str(DATA_DIR / "snapshots" / "snapshot_latest.json")
        if not args.snapshot:
            cmd_capture(args.title, 0, 0, args.roi)
            _sleep_ms(args.sleep_ms)
        out_path = args.out or str(DATA_DIR / "tutorial_decision.json")
        meta = run_tutorial_loop(snapshot_path, args.tutorial_state, args.tutorial_decisions, out_path)
        decision = meta.get("decision")
        if not isinstance(decision, dict):
            print("Decision payload missing.")
            return
        trace_path = Path(args.trace_path) if args.trace_path else None
        log_decision(decision, "tutorial-loop", f"phase:{meta.get('phase', 'unknown')}", path=trace_path)
        results = cmd_decision_execute_file(
            out_path,
            dry_run=args.dry_run,
            snapshot_path=snapshot_path,
            max_actions=args.max_actions,
            seed=args.seed,
        )
        _update_tutorial_state(args.tutorial_state, decision.get("decision_id"), results)
        _sleep_ms(args.sleep_ms)
        cmd_capture(args.title, args.fps, args.seconds, args.roi)
        return
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
        cmd_plan(state, args.model_message, prefer_model=prefer_model, snapshot_path=args.snapshot)
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
        cmd_model_decision(state, args.message, snapshot_path=args.snapshot)
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
    elif cmd == "decision-view":
        cmd_decision_view(args.trace_path, args.limit)
    elif cmd == "decision-tail":
        cmd_decision_tail(args.trace_path, args.limit)
    elif cmd == "decision-export":
        cmd_decision_export(args.trace_path, args.out)
    elif cmd == "decision-rotate":
        cmd_decision_rotate(args.trace_path, args.out_dir)
    elif cmd == "purge-decisions":
        cmd_purge_decisions(args.days)
    elif cmd == "profile-status":
        cmd_profile_status()
    elif cmd == "decision-summary":
        cmd_decision_summary(args.trace_path, args.out)
    elif cmd == "decision-consume":
        cmd_decision_consume(
            args.trace_path,
            snapshot_path=args.snapshot,
            max_actions=args.max_actions,
            seed=args.seed,
        )
    elif cmd == "decision-execute":
        cmd_decision_consume(
            args.trace_path,
            execute="dry-run" if args.dry_run else True,
            snapshot_path=args.snapshot,
            max_actions=args.max_actions,
            seed=args.seed,
        )
    elif cmd == "decision-execute-file":
        cmd_decision_execute_file(
            args.model_output,
            dry_run=args.dry_run,
            snapshot_path=args.snapshot,
            max_actions=args.max_actions,
            seed=args.seed,
        )
    else:
        print("Unknown command. Try: status, ratings, plan, quests, diaries, gear, money, slayer, bossing, profile, import, export, checklist, onboarding, beginner, gearfood, moneyguide, teleports, glossary, readiness, benchmarks, upgrades, estimate, scheduler, risk, pathcompare, questgraph, gui, capture, validate, validate-snapshot, tutorial-loop, go, model, model-decision, profiles, profile-select, profile-status, validate-profiles, validate-model-output, validate-decision-trace, decision-replay, decision-summary, decision-view, decision-tail, decision-export, decision-rotate, decision-consume, decision-execute, decision-execute-file, purge-decisions, score-human, score-human-write, validate-kpi, kpi-append")

    write_overlay(state)
    save_log(f"Command: {cmd}\n")


if __name__ == "__main__":
    main()
