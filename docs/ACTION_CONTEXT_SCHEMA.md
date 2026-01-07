# Action Context Schema

Purpose: define the JSONL schema for action context logs in `logs/action_context.jsonl`.

Each line is a JSON object with the fields below:

- `intent_id`: string
- `decision_id`: string
- `timing`: object (mostly numeric timing values; may include tags such as `idle_action` or `tab_toggle_key`. Examples: `reaction_ms`, `settle_ms`, `dwell_ms`, `hover_dwell_ms`, `click_gap_ms`, `hold_ms`, `scroll_step_delay_ms`, `confidence_pause_ms`, `ui_change_pause_ms`, `double_check_pause_ms`, `interrupt_pause_ms`, `camera_zoom_step`, `camera_zoom_pause_ms`, `fatigue_drift_ms`, `burst_rest_ms`, `hover_check_pause_ms`, `occlusion_wait_ms`, `cadence_ms`, `panic_pause_ms`, `edge_pause_ms`, `offscreen_travel_ms`, `viewport_scan_ms`, `idle_pause_ms`, `idle_recovery_ms`, `focus_recovery`, `idle_action`, `tab_toggle_key`, `typing_bursts`, `typing_corrections`, `typing_overlap_avg_ms`)
- `motion`: object (float values; e.g. `curve_strength`, `micro_jitter_px`, `speed_ramp_mode`, `overshoot_px`, `start_jitter_px`, `edge_margin_px`, `camera_nudge_px`, `camera_overrotate_px`, `camera_slip_px`, `camera_alt_angle_deg`, `camera_alt_path`, `camera_micro_adjust_px`, `attention_drift_dx`, `attention_drift_dy`, `reaim_shifted`, `target_bias`, `target_drift_px`, `retry_reaim_px`)

Notes:
- Produced by `ActionContextLogger` in `src/action_context.py`.
- Only timing/motion hints present on the intent payload are logged.
