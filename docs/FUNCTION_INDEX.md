# Function Index

Generated index of functions and classes in src/

## action_context.py
- log_action_context
- class:ActionContext
- class:ActionContextLogger

## actions.py
- validate_action_intent
- default_backoff_ms
- pre_action_gate
- post_action_verify
- detect_ui_change
- should_abort_action
- should_confirm_irreversible
- should_check_hover_text
- vary_action_order
- requires_confidence_gate
- maybe_settle_before_click
- should_focus_check
- interrupt_delay_ms
- apply_interrupt_pause
- execute_with_retry
- sample_fatigue_drift_ms
- sample_burst_rest_ms
- sample_attention_drift_offset
- execute_dry_run
- requires_approval
- focus_recovery_needed
- build_focus_recovery_intent
- policy_check
- execute_with_policy
- apply_spacing_delay
- class:ActionIntent
- class:ActionResult
- class:ApprovalPolicy
- class:ActionExecutor
- class:DryRunExecutor
- ... and 4 more

## agent_loop.py
- load_json
- select_decision
- cues_met
- run_loop

## agent_runner.py
- save_snapshot
- parse_model_response
- run_agent

## app_cli.py
- save_log
- _write_execution_summary
- _client_bounds_tuple
- _log_bug_ticket
- _capture_stuck_artifacts
- _sleep_ms
- _maybe_seed_session
- _escape_pressed
- _sample_reaction_delay
- _get_client_bounds
- _snapshot_stale
- _prepare_ocr_regions
- _center_point
- _random_point
- _ensure_payload
- _move_cursor
- _idle_profile_from_config
- _apply_focus_recovery
- _apply_edge_pause
- _apply_offscreen_travel
- _apply_viewport_scan
- _apply_idle_action
- _apply_tab_toggle
- _apply_idle_recovery
- _load_action_policy
- _load_approval_policy
- _update_tutorial_state
- _resolve_retry
- _execute_with_retry
- _get_action_label
- ... and 60 more

## arrow_detector.py
- find_yellow_arrow
- find_arrow_target

## attention_drift.py
- apply_attention_drift

## camera_behavior.py
- sample_camera_nudge
- sample_camera_overrotation
- sample_zoom_step
- sample_zoom_pause_ms
- sample_camera_move
- choose_rotation_direction
- apply_camera_drag_slip
- class:CameraProfile

## chat_filter.py
- is_random_event_message
- should_respond_to_chat

## claude_brain.py
- get_client
- analyze_screenshot
- should_use_claude
- hybrid_decide

## cursor_travel.py
- offscreen_travel

## decision_consume.py
- load_decision_entries
- latest_payload
- load_decision_file
- build_action_intents
- validate_intents
- resolve_target_point

## engine.py
- load_json
- get_reference
- validate_state
- migrate_state
- compute_ratings
- detect_bottlenecks
- build_quest_graph
- onboarding_steps
- beginner_quest_bundle
- gear_food_recs
- money_guide
- teleport_checklist
- glossary_terms
- boss_readiness
- efficiency_benchmarks
- gear_upgrade_optimizer
- time_to_goal_estimate
- ironman_constraints
- scheduler_tasks
- generate_plan
- compare_paths
- risk_score

## fast_perception.py
- perceive
- _python_detect
- find_npc
- get_tutorial_phase
- is_player_idle
- rust_available
- class:PerceptionResult

## hardware.py
- _parse_vid_pid
- enumerate_input_devices
- get_display_refresh_rate
- get_input_latency_ms
- class:InputDevice

## human_likeness.py
- score_from_traces
- write_kpi
- validate_kpi_schema
- append_kpi_log

## humanization.py
- _load_json
- load_profiles
- list_profiles
- get_profile
- get_active_profile

## idle_behavior.py
- should_idle_action
- choose_idle_action
- screen_edge_pause
- idle_recovery_sequence
- choose_tab_toggle
- class:IdleBehaviorProfile

## input_exec.py
- _send_input
- _screen_size
- get_cursor_pos
- move_mouse
- move_mouse_path
- click
- scroll
- type_text
- press_key
- press_key_name
- drag
- class:MOUSEINPUT
- class:KEYBDINPUT
- class:INPUT
- class:POINT

## input_noise.py
- sample_polling_jitter_ms
- sample_frame_time_variance_ms
- class:InputNoiseProfile

## input_profiles.py
- default_profile
- apply_overrides
- build_profiles
- class:DeviceProfile

## interrupts.py
- should_pause_on_unexpected_ui
- sample_interruption_delay_ms
- should_panic_on_chat
- class:InterruptProfile

## keyboard.py
- sample_key_delay_ms
- sample_burst_chars
- should_correct_typo
- sample_backspace_ms
- sample_key_overlap_ms
- should_use_modifier
- class:TypingProfile

## librarian_client.py
- get_client
- ask_librarian
- class:LibrarianClient

## librarian_server.py
- main
- class:LibrarianServer

## local_model.py
- load_config
- build_prompt
- build_decision_prompt
- _build_quest_guide_context
- _build_snapshot_context
- _call_ollama
- run_local_model

## minimap.py
- _split_hint
- infer_region

## model_output.py
- extract_json
- validate_planner_output
- log_decision
- validate_decision_trace
- purge_decisions

## mouse_accel.py
- get_profile
- apply_accel
- class:AccelProfile

## mouse_pathing.py
- _ease
- generate_path
- generate_speed_ramp
- jitter_start_point
- add_tremor
- generate_drag_path

## occlusion.py
- is_occluded
- should_wait_for_occlusion
- occlusion_reason

## ocr.py
- register_provider
- get_provider
- run_ocr
- class:OcrEntry
- class:OcrProvider
- class:NoopOcrProvider
- class:TesseractOcrProvider

## pacing.py
- pacing_multiplier
- spacing_from_cues
- adjusted_action_delay

## perception.py
- _get_window_bounds
- _get_window_title
- is_window_focused
- focus_window
- find_windows
- find_window
- capture_frame
- capture_session
- _capture_image
- save_frame
- class:WindowInfo

## quest_guides.py
- load_guides
- _tokenize
- retrieve_guides

## randomness.py
- seed_session

## rhythm.py
- sample_burst_actions
- sample_rest_ms
- apply_fatigue_drift
- maybe_take_break
- class:BurstProfile
- class:SessionRhythmProfile

## runelite_data.py
- read_export
- _normalize_export
- _yaw_to_direction
- is_data_fresh
- get_player_position
- get_camera
- get_compass_direction
- get_npcs
- find_npc_by_name
- find_npc_on_screen
- get_inventory
- has_item
- get_skill_level
- get_tutorial_progress
- get_player_animation
- is_player_idle
- get_tutorial_phase
- build_game_context

## schema_validation.py
- _load_schema
- _check_type
- _validate_object
- validate_state_schema
- validate_snapshot_schema
- validate_humanization_schema
- validate_decision_trace_schema
- validate_human_kpi_log_schema
- validate_tutorial_state_schema
- validate_tutorial_decisions_schema

## scroll.py
- sample_scroll_ticks
- sample_scroll_pause_ms
- class:ScrollProfile

## snapshot.py
- validate_snapshot

## target_acquisition.py
- choose_aim_point
- choose_biased_target

## target_finder.py
- save_screenshot_with_timestamp
- image_to_base64
- find_target_smart
- class:TargetFinder

## targeting.py
- choose_target_with_misclick
- correction_target
- avoid_edges
- reaim_if_shifted

## text_matcher.py
- _similarity
- load_reference
- match_text
- match_tutorial_hint
- class:MatchResult

## timing.py
- _clamp
- sample_gaussian
- sample_reaction_ms
- sample_dwell_ms
- sample_hover_dwell_ms
- sample_jitter_ms
- sample_click_down_up_ms
- sample_long_press_ms
- sample_settle_ms
- sample_think_pause_ms
- sample_handoff_ms
- sample_inter_action_ms
- sample_confirmation_ms
- sample_reaction_ms_for_action
- sample_click_cadence_ms
- sample_double_click_gap_ms
- sample_click_pressure_ms
- sample_drag_start_hesitation_ms
- class:TimingProfile

## ui_detector.py
- register_detector
- get_detector
- detect_ui
- class:UiElement
- class:UiDetector
- class:NoopUiDetector

## ui_scan.py
- build_scan_points
- scan_panel

## ui_state.py
- extract_cursor_state
- extract_hover_text
