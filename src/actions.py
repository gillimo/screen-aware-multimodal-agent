from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import random
import time
from datetime import datetime
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.humanization import get_active_profile

ALLOWED_ACTIONS = {"move", "click", "drag", "type", "scroll", "camera"}


@dataclass
class ActionIntent:
    intent_id: str
    action_type: str
    target: Dict[str, Any]
    confidence: float = 1.0
    required_cues: List[str] = field(default_factory=list)
    gating: Dict[str, Any] = field(default_factory=dict)
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult:
    intent_id: str
    success: bool
    failure_reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalPolicy:
    require_approval: bool = True
    unsafe_actions: List[str] = field(default_factory=lambda: ["drag", "type", "camera"])
    auto_approve_actions: List[str] = field(default_factory=list)


class ActionExecutor:
    def execute(self, intent: ActionIntent) -> ActionResult:
        raise NotImplementedError


class DryRunExecutor(ActionExecutor):
    def execute(self, intent: ActionIntent) -> ActionResult:
        return ActionResult(intent_id=intent.intent_id, success=True, details={"dry_run": True})


class LiveExecutor(ActionExecutor):
    def execute(self, intent: ActionIntent) -> ActionResult:
        from src.decision_consume import resolve_target_point
        from src import input_exec

        try:
            if intent.action_type == "move":
                from src.attention_drift import apply_attention_drift
                from src.targeting import avoid_edges

                point = resolve_target_point(intent.target)
                if point is None:
                    return ActionResult(intent_id=intent.intent_id, success=False, failure_reason="missing_target")
                require_focus = intent.gating.get("require_focus", True)
                if require_focus:
                    snapshot = intent.payload.get("snapshot") if isinstance(intent.payload, dict) else None
                    if not isinstance(snapshot, dict) or not snapshot.get("client", {}).get("focused", False):
                        return ActionResult(intent_id=intent.intent_id, success=False, failure_reason="not_focused")
                profile = get_active_profile() or {}
                motion = profile.get("motion", {}) if isinstance(profile, dict) else {}
                device = profile.get("device", {}) if isinstance(profile, dict) else {}
                noise = profile.get("input_noise", {}) if isinstance(profile, dict) else {}
                attention = profile.get("attention", {}) if isinstance(profile, dict) else {}
                gates = profile.get("gates", {}) if isinstance(profile, dict) else {}
                motion_payload = intent.payload.get("motion") if isinstance(intent.payload, dict) else None
                if not isinstance(motion_payload, dict) and isinstance(intent.payload, dict):
                    motion_payload = {}
                    intent.payload["motion"] = motion_payload
                bounds = intent.target.get("bounds") if isinstance(intent.target, dict) else None
                if isinstance(bounds, dict):
                    from src.target_acquisition import choose_biased_target
                    bias = intent.payload.get("target_bias") if isinstance(intent.payload, dict) else None
                    drift_px = int(intent.payload.get("target_drift_px", 2)) if isinstance(intent.payload, dict) else 2
                    if bias:
                        point = choose_biased_target(bounds, bias=str(bias), drift_px=drift_px)
                        if isinstance(motion_payload, dict):
                            motion_payload.setdefault("target_bias", str(bias))
                            motion_payload.setdefault("target_drift_px", int(drift_px))
                    point = avoid_edges(point, bounds, margin_px=int(motion.get("edge_margin_px", 8)))
                drift_px = float(attention.get("drift_px", 0.0)) if isinstance(attention, dict) else 0.0
                if drift_px > 0:
                    point = apply_attention_drift(
                        point,
                        drift_px=drift_px,
                        bias_x=float(attention.get("bias_x", 0.1)),
                        bias_y=float(attention.get("bias_y", -0.1)),
                    )
                    if isinstance(motion_payload, dict):
                        motion_payload.setdefault("attention_drift_px", drift_px)
                start = input_exec.get_cursor_pos()
                distance = ((point[0] - start[0]) ** 2 + (point[1] - start[1]) ** 2) ** 0.5
                steps = max(6, min(32, int(distance / 12)))
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
                overshoot_rate = float(motion.get("overshoot_rate", 0.0))
                if isinstance(motion_payload, dict):
                    motion_payload.setdefault("curve_strength", curve)
                    motion_payload.setdefault("micro_jitter_px", jitter_px)
                    motion_payload.setdefault("step_delay_ms", step_delay_ms)
                    motion_payload.setdefault("steps", steps)
                    motion_payload.setdefault("start_jitter_px", start_jitter_px)
                    motion_payload.setdefault("edge_margin_px", edge_margin_px)
                    motion_payload.setdefault("speed_ramp_mode", speed_ramp_mode)
                input_exec.move_mouse_path(
                    point[0],
                    point[1],
                    steps=steps,
                    curve_strength=curve,
                    jitter_px=jitter_px,
                    step_delay_ms=step_delay_ms,
                    start_jitter_px=start_jitter_px,
                    edge_margin_px=edge_margin_px,
                    speed_ramp_mode=speed_ramp_mode,
                )
                if overshoot_rate and distance > 24 and random.random() < overshoot_rate:
                    dx = point[0] - start[0]
                    dy = point[1] - start[1]
                    length = max(1.0, (dx ** 2 + dy ** 2) ** 0.5)
                    overshoot_px = max(6.0, distance * random.uniform(0.04, 0.12))
                    ox = int(point[0] + dx / length * overshoot_px)
                    oy = int(point[1] + dy / length * overshoot_px)
                    input_exec.move_mouse_path(
                        ox,
                        oy,
                        steps=max(4, steps // 2),
                        curve_strength=curve,
                        jitter_px=jitter_px,
                        step_delay_ms=step_delay_ms,
                        start_jitter_px=0.0,
                        edge_margin_px=edge_margin_px,
                        speed_ramp_mode=speed_ramp_mode,
                    )
                    input_exec.move_mouse_path(
                        point[0],
                        point[1],
                        steps=max(4, steps // 2),
                        curve_strength=curve,
                        jitter_px=jitter_px,
                        step_delay_ms=step_delay_ms,
                        start_jitter_px=0.0,
                        edge_margin_px=edge_margin_px,
                        speed_ramp_mode=speed_ramp_mode,
                    )
                    if isinstance(motion_payload, dict):
                        motion_payload.setdefault("overshoot_px", float(overshoot_px))
                return ActionResult(intent_id=intent.intent_id, success=True)
            if intent.action_type == "click":
                from src.attention_drift import apply_attention_drift
                from src.targeting import avoid_edges

                profile = get_active_profile() or {}
                timing = profile.get("timing_ms", {}) if isinstance(profile, dict) else {}
                cadence_cfg = timing.get("click_cadence", {}) if isinstance(timing.get("click_cadence"), dict) else {}
                motion = profile.get("motion", {}) if isinstance(profile, dict) else {}
                device = profile.get("device", {}) if isinstance(profile, dict) else {}
                errors_cfg = profile.get("errors", {}) if isinstance(profile, dict) else {}
                noise = profile.get("input_noise", {}) if isinstance(profile, dict) else {}
                attention = profile.get("attention", {}) if isinstance(profile, dict) else {}
                gates = profile.get("gates", {}) if isinstance(profile, dict) else {}
                timing_payload = intent.payload.get("timing") if isinstance(intent.payload, dict) else None
                if not isinstance(timing_payload, dict) and isinstance(intent.payload, dict):
                    timing_payload = {}
                    intent.payload["timing"] = timing_payload
                motion_payload = intent.payload.get("motion") if isinstance(intent.payload, dict) else None
                if not isinstance(motion_payload, dict) and isinstance(intent.payload, dict):
                    motion_payload = {}
                    intent.payload["motion"] = motion_payload
                settle_ms = intent.payload.get("settle_ms")
                if settle_ms is None:
                    settle_cfg = timing.get("settle_ms")
                    if isinstance(settle_cfg, dict):
                        mean = settle_cfg.get("mean", 28)
                        stdev = settle_cfg.get("stdev", 8)
                        min_val = settle_cfg.get("min", 8)
                        max_val = settle_cfg.get("max", 80)
                        settle_ms = max(float(min_val), min(float(max_val), random.gauss(float(mean), float(stdev))))
                    else:
                        mean = timing.get("reaction_mean", 0)
                        stdev = timing.get("reaction_stdev", 0)
                        if mean:
                            settle_ms = max(0.0, random.gauss(float(mean), float(stdev)) * 0.15)
                cadence_context = intent.payload.get("cadence_context") if isinstance(intent.payload, dict) else None
                cadence_ms = None
                if cadence_context and cadence_context in cadence_cfg:
                    mean, stdev, min_val, max_val = cadence_cfg[cadence_context]
                    if stdev <= 0:
                        cadence_ms = max(min_val, min(max_val, mean))
                    else:
                        cadence_ms = random.gauss(mean, stdev)
                        cadence_ms = max(min_val, min(max_val, cadence_ms))
                hover_dwell_ms = intent.payload.get("hover_dwell_ms")
                if hover_dwell_ms is None and isinstance(timing_payload, dict):
                    hover_dwell_ms = timing_payload.get("hover_dwell_ms")
                if hover_dwell_ms is None:
                    hover_cfg = timing.get("hover_dwell_ms")
                    if isinstance(hover_cfg, dict):
                        mean = hover_cfg.get("mean", 32)
                        stdev = hover_cfg.get("stdev", 10)
                        min_val = hover_cfg.get("min", 12)
                        max_val = hover_cfg.get("max", 90)
                        hover_dwell_ms = max(float(min_val), min(float(max_val), random.gauss(float(mean), float(stdev))))
                    else:
                        mean = float(timing.get("reaction_mean", 180)) * 0.12
                        stdev = float(timing.get("reaction_stdev", 60)) * 0.06
                        hover_dwell_ms = max(30.0, random.gauss(mean, stdev))
                if cadence_ms is not None:
                    hover_dwell_ms = max(20.0, cadence_ms * 0.5)
                point = resolve_target_point(intent.target)
                if point is None:
                    return ActionResult(intent_id=intent.intent_id, success=False, failure_reason="missing_target")
                require_focus = intent.gating.get("require_focus")
                if require_focus is None and isinstance(gates, dict):
                    require_focus = gates.get("require_focus", True)
                if require_focus is None:
                    require_focus = True
                if require_focus:
                    snapshot = intent.payload.get("snapshot") if isinstance(intent.payload, dict) else None
                    if not isinstance(snapshot, dict) or not snapshot.get("client", {}).get("focused", False):
                        return ActionResult(intent_id=intent.intent_id, success=False, failure_reason="not_focused")
                expected_hover = intent.gating.get("require_hover_text")
                if expected_hover is None:
                    expected_hover = intent.payload.get("expected_hover_text") if isinstance(intent.payload, dict) else None
                if expected_hover:
                    snapshot = intent.payload.get("snapshot") if isinstance(intent.payload, dict) else None
                    hover_text = ""
                    if isinstance(snapshot, dict):
                        hover_text = snapshot.get("ui", {}).get("hover_text", "")
                    if not hover_text or str(expected_hover).lower() not in str(hover_text).lower():
                        return ActionResult(intent_id=intent.intent_id, success=False, failure_reason="hover_mismatch")
                bounds = intent.target.get("bounds") if isinstance(intent.target, dict) else None
                if isinstance(bounds, dict):
                    point = avoid_edges(point, bounds, margin_px=int(motion.get("edge_margin_px", 8)))
                drift_px = float(attention.get("drift_px", 0.0)) if isinstance(attention, dict) else 0.0
                if drift_px > 0:
                    point = apply_attention_drift(
                        point,
                        drift_px=drift_px,
                        bias_x=float(attention.get("bias_x", 0.1)),
                        bias_y=float(attention.get("bias_y", -0.1)),
                    )
                    if isinstance(motion_payload, dict):
                        motion_payload.setdefault("attention_drift_px", drift_px)
                from src.targeting import choose_target_with_misclick, correction_target
                misclick_rate = float(errors_cfg.get("misclick_rate", 0.0))
                misclick_target, misclicked = choose_target_with_misclick(point, misclick_rate=misclick_rate)
                start = input_exec.get_cursor_pos()
                distance = ((misclick_target[0] - start[0]) ** 2 + (misclick_target[1] - start[1]) ** 2) ** 0.5
                steps = max(6, min(32, int(distance / 12)))
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
                overshoot_rate = float(motion.get("overshoot_rate", 0.0))
                if isinstance(motion_payload, dict):
                    motion_payload.setdefault("curve_strength", curve)
                    motion_payload.setdefault("micro_jitter_px", jitter_px)
                    motion_payload.setdefault("step_delay_ms", step_delay_ms)
                    motion_payload.setdefault("steps", steps)
                    motion_payload.setdefault("start_jitter_px", start_jitter_px)
                    motion_payload.setdefault("edge_margin_px", edge_margin_px)
                    motion_payload.setdefault("speed_ramp_mode", speed_ramp_mode)
                input_exec.move_mouse_path(
                    misclick_target[0],
                    misclick_target[1],
                    steps=steps,
                    curve_strength=curve,
                    jitter_px=jitter_px,
                    step_delay_ms=step_delay_ms,
                    start_jitter_px=start_jitter_px,
                    edge_margin_px=edge_margin_px,
                    speed_ramp_mode=speed_ramp_mode,
                )
                if overshoot_rate and distance > 24 and random.random() < overshoot_rate:
                    dx = misclick_target[0] - start[0]
                    dy = misclick_target[1] - start[1]
                    length = max(1.0, (dx ** 2 + dy ** 2) ** 0.5)
                    overshoot_px = max(6.0, distance * random.uniform(0.04, 0.12))
                    ox = int(misclick_target[0] + dx / length * overshoot_px)
                    oy = int(misclick_target[1] + dy / length * overshoot_px)
                    input_exec.move_mouse_path(
                        ox,
                        oy,
                        steps=max(4, steps // 2),
                        curve_strength=curve,
                        jitter_px=jitter_px,
                        step_delay_ms=step_delay_ms,
                        start_jitter_px=0.0,
                        edge_margin_px=edge_margin_px,
                        speed_ramp_mode=speed_ramp_mode,
                    )
                    input_exec.move_mouse_path(
                        misclick_target[0],
                        misclick_target[1],
                        steps=max(4, steps // 2),
                        curve_strength=curve,
                        jitter_px=jitter_px,
                        step_delay_ms=step_delay_ms,
                        start_jitter_px=0.0,
                        edge_margin_px=edge_margin_px,
                        speed_ramp_mode=speed_ramp_mode,
                    )
                    if isinstance(motion_payload, dict):
                        motion_payload.setdefault("overshoot_px", float(overshoot_px))
                if hover_dwell_ms:
                    time.sleep(float(hover_dwell_ms) / 1000.0)
                if settle_ms:
                    time.sleep(float(settle_ms) / 1000.0)
                button = intent.payload.get("button", "left")
                dwell_ms = intent.payload.get("dwell_ms")
                if dwell_ms is None:
                    dwell_ms = timing.get("click_dwell")
                if cadence_ms is not None:
                    dwell_ms = max(20.0, cadence_ms * 0.7)
                base_dwell = float(dwell_ms) if dwell_ms is not None else 70.0
                pressure_ms = intent.payload.get("pressure_ms")
                if pressure_ms is None:
                    pressure_cfg = timing.get("pressure_ms", {})
                    if isinstance(pressure_cfg, dict):
                        mean = pressure_cfg.get("mean", 12)
                        stdev = pressure_cfg.get("stdev", 4)
                        min_val = pressure_cfg.get("min", 4)
                        max_val = pressure_cfg.get("max", 30)
                        pressure_ms = max(float(min_val), min(float(max_val), random.gauss(float(mean), float(stdev))))
                click_count = int(intent.payload.get("click_count", 1) or 1)
                click_gap_ms = intent.payload.get("click_gap_ms")
                if click_gap_ms is None:
                    click_gap_ms = max(35.0, float(timing.get("reaction_mean", 180)) * 0.08)
                if cadence_ms is not None:
                    click_gap_ms = max(40.0, cadence_ms * 0.6)
                if isinstance(timing_payload, dict):
                    if hover_dwell_ms:
                        timing_payload.setdefault("hover_dwell_ms", float(hover_dwell_ms))
                    if settle_ms is not None:
                        timing_payload.setdefault("settle_ms", float(settle_ms))
                    timing_payload.setdefault("dwell_ms", base_dwell)
                    if pressure_ms is not None:
                        timing_payload.setdefault("pressure_ms", float(pressure_ms))
                    timing_payload.setdefault("click_gap_ms", float(click_gap_ms))
                    timing_payload.setdefault("click_count", int(click_count))
                    if cadence_ms is not None:
                        timing_payload.setdefault("cadence_ms", float(cadence_ms))
                for idx in range(max(1, click_count)):
                    jittered_dwell = max(20.0, random.gauss(base_dwell, max(4.0, base_dwell * 0.18)))
                    jittered_pressure = pressure_ms
                    if pressure_ms is not None:
                        jittered_pressure = max(1.0, random.gauss(float(pressure_ms), max(1.0, float(pressure_ms) * 0.25)))
                    input_exec.click(button, dwell_ms=jittered_dwell, pressure_ms=jittered_pressure)
                    if idx < click_count - 1:
                        time.sleep(float(click_gap_ms) / 1000.0)
                correction_rate = float(errors_cfg.get("correction_rate", 0.0))
                if misclicked and correction_rate and random.random() < correction_rate:
                    correction_point = correction_target(point, misclicked)
                    input_exec.move_mouse_path(
                        correction_point[0],
                        correction_point[1],
                        steps=steps,
                        curve_strength=curve,
                        jitter_px=jitter_px,
                        step_delay_ms=step_delay_ms,
                    )
                    time.sleep(random.uniform(0.04, 0.18))
                    input_exec.click(button, dwell_ms=base_dwell, pressure_ms=pressure_ms)
                return ActionResult(intent_id=intent.intent_id, success=True)
            if intent.action_type == "scroll":
                from src.scroll import ScrollProfile, sample_scroll_pause_ms, sample_scroll_ticks

                payload = intent.payload if isinstance(intent.payload, dict) else {}
                amount = int(payload.get("amount", 1))
                profile = get_active_profile() or {}
                timing = profile.get("timing_ms", {}) if isinstance(profile, dict) else {}
                scroll_cfg = profile.get("scroll", {}) if isinstance(profile, dict) else {}
                ticks_cfg = scroll_cfg.get("ticks") if isinstance(scroll_cfg, dict) else None
                pause_cfg = scroll_cfg.get("pause_ms") if isinstance(scroll_cfg, dict) else None
                scroll_profile = ScrollProfile(
                    ticks=tuple(ticks_cfg) if isinstance(ticks_cfg, (list, tuple)) and len(ticks_cfg) == 4 else ScrollProfile().ticks,
                    pause_ms=tuple(pause_cfg) if isinstance(pause_cfg, (list, tuple)) and len(pause_cfg) == 4 else ScrollProfile().pause_ms,
                )
                timing_payload = payload.get("timing") if isinstance(payload, dict) else None
                if not isinstance(timing_payload, dict) and isinstance(payload, dict):
                    timing_payload = {}
                    payload["timing"] = timing_payload
                base_delay = max(20.0, float(timing.get("reaction_mean", 180)) * 0.08)
                jitter = max(6.0, float(timing.get("reaction_stdev", 60)) * 0.05)
                step_delay_ms = payload.get("step_delay_ms")
                if step_delay_ms is None:
                    step_delay_ms = max(15.0, random.gauss(base_delay, jitter))
                steps = max(1, abs(amount))
                direction = 1 if amount >= 0 else -1
                if isinstance(timing_payload, dict):
                    timing_payload.setdefault("scroll_step_delay_ms", float(step_delay_ms))
                    timing_payload.setdefault("scroll_steps", int(steps))
                    timing_payload.setdefault("scroll_amount", int(amount))
                for idx in range(steps):
                    input_exec.scroll(direction)
                    if idx < steps - 1:
                        pause_ms = sample_scroll_pause_ms(scroll_profile)
                        if pause_ms <= 0:
                            pause_ms = float(step_delay_ms)
                        time.sleep(float(pause_ms) / 1000.0)
                return ActionResult(intent_id=intent.intent_id, success=True)
            if intent.action_type == "type":
                from src.keyboard import TypingProfile, sample_key_delay_ms

                payload = intent.payload if isinstance(intent.payload, dict) else {}
                text = str(payload.get("text", ""))
                delay = payload.get("delay_ms")
                profile = get_active_profile() or {}
                typing_cfg = profile.get("typing", {}) if isinstance(profile, dict) else {}
                delays_cfg = typing_cfg.get("key_delay_ms") if isinstance(typing_cfg, dict) else None
                typing_profile = TypingProfile(
                    key_delay_ms=tuple(delays_cfg)
                    if isinstance(delays_cfg, (list, tuple)) and len(delays_cfg) == 4
                    else TypingProfile().key_delay_ms
                )
                timing_payload = payload.get("timing") if isinstance(payload, dict) else None
                if not isinstance(timing_payload, dict) and isinstance(payload, dict):
                    timing_payload = {}
                    payload["timing"] = timing_payload
                if delay:
                    input_exec.type_text(text, delay_ms=int(delay))
                else:
                    delays = []
                    for ch in text:
                        key_delay = max(10.0, sample_key_delay_ms(typing_profile))
                        delays.append(key_delay)
                        input_exec.type_text(ch, delay_ms=int(key_delay))
                    if delays and isinstance(timing_payload, dict):
                        timing_payload.setdefault("typing_avg_delay_ms", float(sum(delays) / len(delays)))
                        timing_payload.setdefault("typing_chars", len(text))
                return ActionResult(intent_id=intent.intent_id, success=True)
            if intent.action_type == "drag":
                start = intent.payload.get("start")
                end = intent.payload.get("end")
                if not isinstance(start, (list, tuple)) or not isinstance(end, (list, tuple)):
                    return ActionResult(intent_id=intent.intent_id, success=False, failure_reason="missing_drag_points")
                timing_payload = intent.payload.get("timing") if isinstance(intent.payload, dict) else None
                if not isinstance(timing_payload, dict) and isinstance(intent.payload, dict):
                    timing_payload = {}
                    intent.payload["timing"] = timing_payload
                hold_ms = intent.payload.get("hold_ms")
                if hold_ms is None:
                    profile = get_active_profile() or {}
                    timing = profile.get("timing_ms", {}) if isinstance(profile, dict) else {}
                    base_dwell = float(timing.get("click_dwell", 70))
                    hold_ms = max(40.0, random.gauss(base_dwell * 1.4, max(6.0, base_dwell * 0.2)))
                    if isinstance(timing_payload, dict):
                        timing_payload.setdefault("hold_ms", float(hold_ms))
                hesitation_ms = intent.payload.get("hesitation_ms")
                if hesitation_ms is None:
                    profile = get_active_profile() or {}
                    timing = profile.get("timing_ms", {}) if isinstance(profile, dict) else {}
                    base_hesitation = max(20.0, float(timing.get("reaction_mean", 180)) * 0.12)
                    hesitation_ms = max(15.0, random.gauss(base_hesitation, base_hesitation * 0.2))
                if isinstance(timing_payload, dict):
                    timing_payload.setdefault("hesitation_ms", float(hesitation_ms))
                if hesitation_ms:
                    time.sleep(float(hesitation_ms) / 1000.0)
                input_exec.drag((int(start[0]), int(start[1])), (int(end[0]), int(end[1])), hold_ms=hold_ms)
                profile = get_active_profile() or {}
                motion = profile.get("motion", {}) if isinstance(profile, dict) else {}
                end_jitter_px = intent.payload.get("end_jitter_px")
                if end_jitter_px is None:
                    end_jitter_px = float(motion.get("micro_jitter_px", 0.0))
                if end_jitter_px:
                    jitter_x = int(random.uniform(-end_jitter_px, end_jitter_px))
                    jitter_y = int(random.uniform(-end_jitter_px, end_jitter_px))
                    input_exec.move_mouse(int(end[0]) + jitter_x, int(end[1]) + jitter_y)
                return ActionResult(intent_id=intent.intent_id, success=True)
            if intent.action_type == "camera":
                payload = intent.payload if isinstance(intent.payload, dict) else {}
                timing_payload = payload.get("timing") if isinstance(payload.get("timing"), dict) else None
                if not isinstance(timing_payload, dict) and isinstance(intent.payload, dict):
                    timing_payload = {}
                    intent.payload["timing"] = timing_payload
                motion_payload = payload.get("motion") if isinstance(payload.get("motion"), dict) else None
                if not isinstance(motion_payload, dict) and isinstance(intent.payload, dict):
                    motion_payload = {}
                    intent.payload["motion"] = motion_payload
                from src.camera_behavior import (
                    CameraProfile,
                    sample_camera_nudge,
                    sample_camera_overrotation,
                    sample_zoom_step,
                    sample_zoom_pause_ms,
                    apply_camera_drag_slip,
                )
                camera_profile = CameraProfile()
                drag_payload = payload.get("drag") if isinstance(payload.get("drag"), dict) else None
                if drag_payload:
                    start = drag_payload.get("start")
                    end = drag_payload.get("end")
                    hold_ms = drag_payload.get("hold_ms")
                else:
                    start = payload.get("start")
                    end = payload.get("end")
                    hold_ms = payload.get("hold_ms")
                if isinstance(start, (list, tuple)) and isinstance(end, (list, tuple)):
                    nudge_px = sample_camera_nudge(camera_profile)
                    over_px = sample_camera_overrotation(camera_profile)
                    slip_px = apply_camera_drag_slip(0.0, slip_deg=camera_profile.overrotate_deg)
                    adjusted_end = (
                        int(end[0] + nudge_px + over_px),
                        int(end[1] + slip_px),
                    )
                    profile = get_active_profile() or {}
                    motion_cfg = profile.get("motion", {}) if isinstance(profile, dict) else {}
                    alt_chance = float(motion_cfg.get("camera_alt_path_chance", 0.0))
                    alt_angle = float(motion_cfg.get("camera_alt_angle_deg", 0.0))
                    if alt_chance > 0 and alt_angle > 0 and random.random() < alt_chance:
                        angle = math.radians(random.choice([-alt_angle, alt_angle]))
                        dx = adjusted_end[0] - int(start[0])
                        dy = adjusted_end[1] - int(start[1])
                        rot_dx = dx * math.cos(angle) - dy * math.sin(angle)
                        rot_dy = dx * math.sin(angle) + dy * math.cos(angle)
                        adjusted_end = (int(start[0] + rot_dx), int(start[1] + rot_dy))
                        if isinstance(motion_payload, dict):
                            motion_payload.setdefault("camera_alt_angle_deg", float(alt_angle))
                            motion_payload.setdefault("camera_alt_path", True)
                    if isinstance(motion_payload, dict):
                        motion_payload.setdefault("camera_nudge_px", float(nudge_px))
                        motion_payload.setdefault("camera_overrotate_px", float(over_px))
                        motion_payload.setdefault("camera_slip_px", float(slip_px))
                    input_exec.drag((int(start[0]), int(start[1])), adjusted_end, hold_ms=hold_ms)
                    return ActionResult(intent_id=intent.intent_id, success=True)
                amount = payload.get("amount")
                if amount is not None:
                    steps = max(1, abs(int(amount)))
                    direction = 1 if int(amount) >= 0 else -1
                    zoom_step = sample_zoom_step(camera_profile)
                    zoom_pause_ms = sample_zoom_pause_ms(camera_profile)
                    if isinstance(timing_payload, dict):
                        timing_payload.setdefault("camera_zoom_step", int(zoom_step))
                        timing_payload.setdefault("camera_zoom_pause_ms", int(zoom_pause_ms))
                    for idx in range(steps):
                        input_exec.scroll(direction * abs(int(zoom_step)))
                        if idx < steps - 1:
                            time.sleep(float(zoom_pause_ms) / 1000.0)
                    return ActionResult(intent_id=intent.intent_id, success=True)
                return ActionResult(intent_id=intent.intent_id, success=False, failure_reason="missing_camera_payload")
            return ActionResult(intent_id=intent.intent_id, success=False, failure_reason="unsupported_action")
        except Exception as exc:
            return ActionResult(intent_id=intent.intent_id, success=False, failure_reason=str(exc))


class ActionLogger:
    def __init__(self, path: Optional[Path] = None):
        if path is None:
            root = Path(__file__).resolve().parents[1]
            path = root / "logs" / "actions.jsonl"
        path.parent.mkdir(exist_ok=True)
        self.path = path

    def log(self, intent: ActionIntent, result: ActionResult) -> None:
        profile = get_active_profile()
        if profile and "humanization_profile" not in intent.payload:
            intent.payload["humanization_profile"] = profile
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "intent": intent.__dict__,
            "result": result.__dict__,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")


def validate_action_intent(intent: ActionIntent) -> List[str]:
    errors: List[str] = []
    if intent.action_type not in ALLOWED_ACTIONS:
        errors.append(f"unsupported action_type: {intent.action_type}")
    if not isinstance(intent.target, dict) or not intent.target:
        errors.append("target must be a non-empty object")
    if not 0 <= intent.confidence <= 1:
        errors.append("confidence must be between 0 and 1")
    return errors


def default_backoff_ms(attempt: int, base_ms: int = 120, max_ms: int = 800) -> int:
    return min(max_ms, base_ms * attempt)


def pre_action_gate(intent: ActionIntent, snapshot: Optional[Dict[str, Any]] = None) -> List[str]:
    errors: List[str] = []
    if snapshot is None:
        return errors

    if "ui" not in snapshot or not isinstance(snapshot.get("ui"), dict):
        errors.append("snapshot missing ui")
    if "client" not in snapshot or not isinstance(snapshot.get("client"), dict):
        errors.append("snapshot missing client")

    client = snapshot.get("client", {})
    ui = snapshot.get("ui", {})
    cues = snapshot.get("cues", {})

                require_focus = intent.gating.get("require_focus")
                if require_focus is None and isinstance(gates, dict):
                    require_focus = gates.get("require_focus", True)
                if require_focus is None:
                    require_focus = True
    if require_focus and not client.get("focused", False):
        errors.append("client not focused")

    require_hover = intent.gating.get("require_hover_text")
    if require_hover:
        actual = ui.get("hover_text", "")
        if require_hover.lower() not in actual.lower():
            errors.append("hover_text mismatch")

    require_open = intent.gating.get("require_open_interface")
    if require_open:
        if ui.get("open_interface") != require_open:
            errors.append("open_interface mismatch")

    for cue in intent.required_cues:
        val = cues.get(cue)
        if not val or str(val).lower() in {"none", "unknown"}:
            errors.append(f"missing cue {cue}")
    return errors


def post_action_verify(
    intent: ActionIntent,
    snapshot_after: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    if snapshot_after is None:
        return False, "no_post_snapshot"

    ui = snapshot_after.get("ui", {})
    expect_open = intent.gating.get("expect_open_interface")
    if expect_open and ui.get("open_interface") != expect_open:
        return False, "expected_interface_missing"

    expect_cursor = intent.gating.get("expect_cursor_state")
    if expect_cursor and ui.get("cursor_state") != expect_cursor:
        return False, "expected_cursor_state_missing"

    return True, ""


def detect_ui_change(
    snapshot_before: Optional[Dict[str, Any]],
    snapshot_after: Optional[Dict[str, Any]],
) -> List[str]:
    errors: List[str] = []
    if snapshot_before is None or snapshot_after is None:
        return errors
    ui_before = snapshot_before.get("ui", {})
    ui_after = snapshot_after.get("ui", {})
    cues_before = snapshot_before.get("cues", {})
    cues_after = snapshot_after.get("cues", {})

    if ui_before.get("open_interface") != ui_after.get("open_interface"):
        errors.append("open_interface_changed")
    if cues_before.get("modal_state") != cues_after.get("modal_state"):
        errors.append("modal_state_changed")
    return errors


def should_abort_action(
    snapshot_before: Optional[Dict[str, Any]],
    snapshot_after: Optional[Dict[str, Any]],
) -> bool:
    if snapshot_before is None or snapshot_after is None:
        return False

    ui_before = snapshot_before.get("ui", {})
    ui_after = snapshot_after.get("ui", {})
    cues_before = snapshot_before.get("cues", {})
    cues_after = snapshot_after.get("cues", {})

    if ui_before.get("open_interface") != ui_after.get("open_interface"):
        return True
    if cues_before.get("modal_state") != cues_after.get("modal_state"):
        return True
    return False


def should_confirm_irreversible(action_label: str, chance: float = 0.7) -> bool:
    irreversible = {"drop", "alch", "trade"}
    if action_label not in irreversible:
        return False
    return random.random() < chance


def should_check_hover_text(chance: float = 0.6) -> bool:
    return random.random() < chance


def vary_action_order(actions: List[Any], variability_rate: float = 0.2) -> List[Any]:
    if variability_rate <= 0 or len(actions) < 2:
        return list(actions)
    if random.random() < variability_rate:
        shuffled = list(actions)
        random.shuffle(shuffled)
        return shuffled
    return list(actions)


def requires_confidence_gate(intent: ActionIntent, threshold: float = 0.6) -> bool:
    return intent.confidence < threshold


def maybe_settle_before_click(
    intent: ActionIntent,
    settle_ms: float,
    sleep_fn=None,
) -> None:
    if intent.action_type != "click":
        return
    if sleep_fn is None:
        return
    if settle_ms > 0:
        sleep_fn(settle_ms / 1000.0)


def should_focus_check(chance: float = 0.3) -> bool:
    return random.random() < chance


def interrupt_delay_ms(snapshot: Optional[Dict[str, Any]], profile) -> float:
    from src.interrupts import should_pause_on_unexpected_ui, sample_interruption_delay_ms

    if snapshot is None:
        return 0.0
    if should_pause_on_unexpected_ui(snapshot):
        return sample_interruption_delay_ms(profile)
    return 0.0


def apply_interrupt_pause(
    snapshot: Optional[Dict[str, Any]],
    profile,
    sleep_fn=None,
) -> float:
    delay_ms = interrupt_delay_ms(snapshot, profile)
    if delay_ms and sleep_fn is not None:
        sleep_fn(delay_ms / 1000.0)
    return delay_ms


def execute_with_retry(
    executor: ActionExecutor,
    intent: ActionIntent,
    verify_fn=None,
    max_attempts: int = 2,
    backoff_fn=None,
    sleep_fn=None,
) -> ActionResult:
    last_reason = ""
    for attempt in range(1, max_attempts + 1):
        profile = get_active_profile()
        if profile and "humanization_profile" not in intent.payload:
            intent.payload["humanization_profile"] = profile
        result = executor.execute(intent)
        if verify_fn is None:
            result.details["attempts"] = attempt
            return result

        ok, reason = verify_fn(intent)
        if ok:
            return ActionResult(intent_id=intent.intent_id, success=True, details={"attempts": attempt})
        last_reason = reason

        if backoff_fn is not None and sleep_fn is not None:
            backoff_ms = backoff_fn(attempt)
            if backoff_ms:
                sleep_fn(backoff_ms / 1000.0)

    return ActionResult(
        intent_id=intent.intent_id,
        success=False,
        failure_reason=last_reason or "post_check_failed",
        details={"attempts": max_attempts},
    )


def sample_fatigue_drift_ms(profile, action_index: int) -> float:
    if not isinstance(profile, dict):
        return 0.0
    session = profile.get("session", {}) if isinstance(profile.get("session"), dict) else {}
    drift_rate = float(session.get("fatigue_drift_rate", 0.0))
    if drift_rate <= 0:
        return 0.0
    base = float(session.get("rest_mean_ms", 0.0))
    if base <= 0:
        return 0.0
    drift_ms = base * drift_rate * max(0, action_index)
    return max(0.0, drift_ms)


def sample_burst_rest_ms(profile) -> float:
    if not isinstance(profile, dict):
        return 0.0
    session = profile.get("session", {}) if isinstance(profile.get("session"), dict) else {}
    rest_mean = float(session.get("rest_mean_ms", 0.0))
    rest_sigma = float(session.get("rest_stdev_ms", rest_mean * 0.35 if rest_mean else 0.0))
    if rest_mean <= 0:
        return 0.0
    rest = random.gauss(rest_mean, rest_sigma)
    return max(0.0, rest)


def sample_attention_drift_offset(profile, action_index: int) -> tuple[float, float]:
    if not isinstance(profile, dict):
        return 0.0, 0.0
    session = profile.get("session", {}) if isinstance(profile.get("session"), dict) else {}
    drift_rate = float(session.get("attention_drift_rate", 0.0))
    if drift_rate <= 0:
        return 0.0, 0.0
    magnitude = drift_rate * max(1, action_index)
    dx = random.uniform(-magnitude, magnitude)
    dy = random.uniform(-magnitude, magnitude)
    return dx, dy


def execute_dry_run(intent: ActionIntent, logger: Optional[ActionLogger] = None) -> ActionResult:
    profile = get_active_profile()
    if profile and isinstance(intent.payload, dict):
        intent.payload["humanization_profile"] = profile
    executor = DryRunExecutor()
    result = executor.execute(intent)
    if logger is not None:
        logger.log(intent, result)
    return result


def requires_approval(intent: ActionIntent, policy: ApprovalPolicy) -> bool:
    if not policy.require_approval:
        return False
    if intent.action_type in policy.auto_approve_actions:
        return False
    return intent.action_type in policy.unsafe_actions


def focus_recovery_needed(snapshot: Optional[Dict[str, Any]]) -> bool:
    if not snapshot or "client" not in snapshot:
        return True
    return not snapshot.get("client", {}).get("focused", False)


def build_focus_recovery_intent(
    x: int,
    y: int,
    intent_id: str = "focus_recovery",
) -> ActionIntent:
    return ActionIntent(
        intent_id=intent_id,
        action_type="click",
        target={"x": x, "y": y},
        confidence=1.0,
        gating={"require_focus": False},
    )

@dataclass
class ActionPolicy:
    allowed_actions: List[str] = field(default_factory=lambda: list(ALLOWED_ACTIONS))
    cooldown_ms: int = 0
    rate_limit_per_min: int = 0


class ActionRateLimiter:
    def __init__(self, policy: ActionPolicy):
        self.policy = policy
        self.timestamps: List[float] = []

    def allow(self, now_s: float) -> bool:
        if self.policy.rate_limit_per_min <= 0:
            return True
        window_start = now_s - 60.0
        self.timestamps = [t for t in self.timestamps if t >= window_start]
        if len(self.timestamps) >= self.policy.rate_limit_per_min:
            return False
        self.timestamps.append(now_s)
        return True


def policy_check(intent: ActionIntent, policy: ActionPolicy) -> List[str]:
    errors: List[str] = []
    if intent.action_type not in policy.allowed_actions:
        errors.append("action_type not allowed by policy")
    return errors


def execute_with_policy(
    executor: ActionExecutor,
    intent: ActionIntent,
    policy: ActionPolicy,
    rate_limiter: Optional[ActionRateLimiter] = None,
    now_s: Optional[float] = None,
    settle_ms: float = 0.0,
    sleep_fn=None,
) -> ActionResult:
    errors = policy_check(intent, policy)
    if errors:
        return ActionResult(intent_id=intent.intent_id, success=False, failure_reason="policy_block")
    if rate_limiter is not None and now_s is not None:
        if not rate_limiter.allow(now_s):
            return ActionResult(intent_id=intent.intent_id, success=False, failure_reason="rate_limited")
    if settle_ms and sleep_fn is not None:
        maybe_settle_before_click(intent, settle_ms, sleep_fn=sleep_fn)
    result = executor.execute(intent)
    result.details.setdefault("timestamp", datetime.utcnow().isoformat() + "Z")
    return result


def apply_spacing_delay(
    base_ms: float,
    cues: Optional[Dict[str, object]],
    context: str = "default",
) -> float:
    from src.pacing import adjusted_action_delay

    return adjusted_action_delay(base_ms, cues or {}, context=context)
