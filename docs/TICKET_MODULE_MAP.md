# Ticket to Module Map

Purpose: map tickets in docs/TICKETS.md to the modules they primarily belong to.

Note: some tickets span modules; listed under the module that owns the main implementation.

## Core Loop Orchestration
- Make the JSON action-intent loop the default automation path; keep free-text commands test-only.
- Ensure snapshot capture outputs `SNAPSHOT_SCHEMA.md` fields (client, roi, cues, derived, account, stale, runelite_data) or add an adapter layer.
- Wire decision validation + trace logging into the canonical loop before execution.
- Execute intents through policy/approval gating and log action context + execution summaries in the same loop.
- Align tutorial loop orchestration with the canonical action-intent pipeline (state updates, cues, and decision replay).
- Retire or fix legacy loop timing issues (e.g., double sleep) once canonical loop owns timing.
- Define RSProx-first pipeline stages with explicit timing budgets and short-circuit rules.
- Gate heavy OCR/snapshot capture behind stuck/uncertain triggers; keep RSProx hot path lightweight.
- Define fallback triggers (stuck, low-confidence, verification failures) and recovery flow.
- Establish minimal normalization contract for model/executor input; add optional enrichment path.
- Define logging boundaries for hot path vs fallback (always-on vs on-demand logs).

## Data and Models
- Add project-specific datasets in data/reference.json.
- Expand dependency graph for key workflows.
- Implement model integration in src/local_model.py.
- Add schema validation checks for `data/state.json` in the CLI.
- Define model output/decision schema for planner and action intents.
- Add strict JSON retry policy config (max attempts) for model outputs.

## Perception Pipeline
- Build screen capture pipeline with configurable FPS and region-of-interest support.
- Add an OCR layer with a pluggable backend (local model or external provider).
- Add OCR config file and provider hook (noop/tesseract) with basic calibration helper.
- Add a UI element detector pipeline for buttons, minimap, chat, and inventory slots.
- Implement state extraction into a normalized UI snapshot schema with timestamps.
- Add a capture and annotate tool for labeling screens to improve UI detection.
- Add visual cue extraction for animations, hover text, highlights, and overlays.
- Add structured-state augmentation pipeline (merge JSON state with visual cues).
- Add schema validation for snapshot payloads in perception pipeline.

## Planning and Memory
- Create a short-term planner (single-session goals, next action selection).
- Create a medium-term planner (quest, leveling, or skilling milestones).
- Create a long-term planner (account progression roadmap, week/month targets).
- Implement a plan store (JSONL) with revision history and rationale fields.
- Build a task scheduler to prioritize near-term actions while respecting long-term goals.
- Add a skill/ability model that maps account stats, gear, and unlocks to action viability.
- Add a feedback loop: action result -> updated state -> plan adjustment.

## Input and Execution (Core)
- Implement action executor interfaces (mouse move/click, keyboard input, camera control).

### Input: Timing and Rhythm
- Add variable click timing (jitter and configurable distributions) for input actions.
- Add reaction-time model (stimulus-to-action delay) with per-action distributions.
- Add inter-action micro-pauses based on task complexity and recent activity.
- Add handoff latency between mouse and keyboard actions.
- Add session rhythm modeling (breaks, fatigue, time-based drift).
- Add repetition breakers to vary timing/pathing across repeated actions.
- Add stochastic delay after action completion (human confirmation pause).
- Add input burst modeling (short spurts followed by rest).
- Add action spacing based on in-game animations or cooldown cues.
- Add context-based pacing (slow down in complex scenes, speed up in simple ones).
- Add context-specific click cadence presets (banking vs. skilling).
- Add shift-queue timing variance for repeated actions.

### Input: Mouse Movement
- Add non-linear mouse pathing (curves and easing) for mouse move actions.
- Add hover dwell before click to simulate target acquisition.
- Add occasional mouse overshoot with corrective micro-moves.
- Add click down/up dwell variance and long-press support for drag actions.
- Add misclick/near-miss modeling with corrective behavior (configurable rate).
- Add scroll wheel speed variance and pause patterns for scroll actions.
- Add mouse acceleration profiles (DPI, OS speed, accel curve) with presets.
- Add camera nudge variability instead of always perfect positioning.
- Add focus checks (re-hover or re-read UI state) before committing actions.
- Add per-user behavior profiles (timing, movement, mistakes) to avoid a single signature.
- Add stochastic idle behaviors (hover, camera glance, inventory check) within safe bounds.
- Add UI scan patterns before actions (mouse sweep or hover checks).
- Add hesitation mechanics before high-impact actions (bank, trade, drop).
- Add corrective camera adjustments after minor overshoot or misclick.
- Add target acquisition model (aim point selection within UI bounds).
- Add action chaining variability (different orderings for equivalent steps).
- Add attention drift model that slightly biases cursor paths over time.
- Add safe interrupt handling (pause on unexpected UI, resume with re-check).
- Add reaction to interruptions (randomized delay or abort on new modal).
- Add human-like camera movement (short nudges, occasional over-rotation).
- Add UI focus recovery (click back into client if focus lost).
- Add gesture variability for drag actions (speed, curvature, end jitter).
- Add per-action confidence gating (extra checks when uncertainty is high).
- Add cursor settle behavior (brief stillness before final click).
- Add edge avoidance for mouse paths (avoid perfectly straight to corners).
- Add double-click variance for UI actions that use multi-click patterns.
- Add drag start hesitation and end jitter (human-like drag endpoints).
- Add click targeting bias toward text center or icon center with drift.
- Add long idle recovery behavior (re-orient UI, re-check state).
- Add screen edge pauses (cursor leaves client briefly, returns).
- Add off-screen cursor travel patterns for modal dismissal or refocus.
- Add viewport scanning before interacting with new UI panels.
- Add user-like camera zoom variation with pauses.
- Add retry strategy for failed interactions (back off, re-aim, re-try).
- Add action abort behavior when UI changes mid-action.
- Add cursor speed ramps (accelerate/decay rather than constant velocity).
- Add micro-tremor noise in slow cursor movements (sub-pixel jitter).
- Add target re-aim when hitbox shifts (moving entities).
- Add element occlusion handling (wait or reposition when obstructed).
- Add human slips in camera drag (slight vertical drift).
- Add randomized start point for mouse moves (from last idle position).
- Add edge-of-screen bounce avoidance for cursor travel.
- Add alternate pathing for camera rotation (different drag directions).

### Input: Keyboard
- Add typing cadence modeling (key delays, bursts, corrections, backspace).
- Add keypress overlap modeling (shift+click timing variance).
- Add modifier key usage variance (shift, ctrl) where applicable.

### Input: Device and Signals
- Add input device noise model (USB polling jitter, frame-time variance).
- Add per-session seed control for reproducible randomness in testing.
- Add configurable humanization presets (subtle, normal, heavy).
- Add action context logger for timing/motion features to enable tuning.
- Add decision_id to action context logs for run correlation.

### Input: Decision Friction
- Add click pressure simulation (down/up cadence by action type).
- Add probabilistic check of hover text before click.
- Add short thinking pauses after UI state changes.
- Add double-check loop for irreversible actions (drop, alch, trade).
- Add panic pause on unexpected chat or trade window.
- Add action abort behavior when UI changes mid-action.

### Input: Session Behaviors
- Add long idle recovery behavior (re-orient UI, re-check state).
- Add periodic UI tab toggles (inventory, skills, quests) when idle.
- Add screen edge pauses (cursor leaves client briefly, returns).
- Add off-screen cursor travel patterns for modal dismissal or refocus.

## Safety and Policy
- Add a policy layer for allowed action types, rate limits, and cooldowns.
- Add a human-in-the-loop mode with step-by-step approval toggles.
- Add a sandbox action mode for dry runs that logs actions without executing them.
- Add an emergency stop key (Esc) to abort execution loops for regaining control.

## Chat and Social
- Add local-model chat responses when a player name is detected (opt-in, rate-limited, context-aware).
- Add chat cooldown rules (per player, per session, per channel).

## UI and Overlay
- Build a silent, click-through overlay for the OSRS original client (no RuneLite dependency).
- Ensure overlay can attach to the OSRS client window and track resize/move.
- Design a GUI control panel with presets (e.g., Make best money, Train for best money, Quest unlock path).
- Implement GUI presets mapping to planner goals and constraints.
- Add a custom goal builder UI (select skills, target levels, time budget, risk tolerance).
- Add a session summary panel showing chosen preset, planned steps, and expected outcomes.
- Add accessibility options for the agent UI (font size scaling, high-contrast theme, reduced motion).
- Add configurable UI hotkeys for common actions (start, pause, next step, open logs).
- Add screen reader labels and focus order for all GUI controls.

## Logging, Replay, and Profiling
- Add structured logging for every decision and action with timestamps.
- Add decision trace viewer UI (minimal CLI/TUI) for log inspection.
- Add scheduled compression/rotation for decision logs.
- Build replay tooling to review sessions from logs and screenshots.
- Implement performance profiling for capture, OCR, and planning loops.
- Add a monitoring/audit log spec that records inputs, decisions, and actions for post-run review.
- Add evaluation comparing structured-only vs. visual-augmented behavior.

## Metrics and Evaluation
- Define stimulus parity requirements (visual cues vs. structured JSON inputs).
- Add perception parity checks to ensure agent reacts to on-screen cues.
- Add human-like pacing model tied to animation and UI feedback cues.
- Define calibration workflow for human-like baselines (data capture, fitting, review).
- Ingest human-likeness KPI output into metrics reporting.
- Apply HUMAN_MIMICRY_RUBRIC per run and persist scores (e.g., logs/mimicry_scores.jsonl).
- Create Mimicry and Model acceptance checklist tied to END_STATE goals.

## Testing and Documentation
- Add unit tests for planner logic and state parsing.
- Add integration tests with recorded screen sessions.
- Extend docs for vision, scope, and operational workflow of the agent.
- Add a compliance review section in docs covering acceptable use, user consent, and risk boundaries.
- Add a safety checklist for any deployment or live testing (manual review steps, rollback plan).
- Define end-to-end architecture for a screen-aware agent (modules, data flow, storage, failure modes).
- Define `SCHEMAS.md` as the source of truth for all schema docs.
- Add and maintain `STATE_SCHEMA.md` for `data/state.json`.
- Add and maintain `SNAPSHOT_SCHEMA.md` for screen-aware snapshots.
- Create an end-state acceptance checklist tying END_STATE goals to ticket completion.
- Define data retention/privacy policy for action traces and screenshots.
- Create a Mimicry and Model overview doc that consolidates scope, schemas, tickets, and dependencies.

## Input and Execution (Core)
### Input: Device and Signals
- Add configuration storage for humanization presets and per-user profiles.
- Enforce active humanization profile in live executor (non-dry-run).
