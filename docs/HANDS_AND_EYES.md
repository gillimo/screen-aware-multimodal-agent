# Hands and Eyes Requirements (AgentOSRS)

Purpose: define the perception ("eyes") and action ("hands") needs for a screen-aware OSRS agent, plus the focused ticket backlog.

## Scope
- Eyes: capture what is on screen, read UI text, and produce a trusted state snapshot.
- Hands: execute input actions only when allowed, with safety checks and auditable logs.
- Safety: default to observation-only unless explicit execution is enabled.

## Eyes (Perception) Needs

### Capture
- Detect the OSRS client window, bounds, focus, and scale.
- Capture frames at configurable FPS with ROI support.
- Record capture latency and dropped-frame counts.

### UI Parsing
- Identify core panels: minimap, chatbox, inventory, skills, quests, bank, shop.
- Detect interactable UI elements (buttons, slots, tabs) with bounding boxes.
- Track cursor state and hover text.

### OCR
- Read chat lines, system messages, dialogue text, and hover tooltips.
- Extract interface labels and item names when visible.
- Provide per-region OCR confidence scores.

### Derived State
- Infer location and sub-area hints from minimap and landmarks.
- Determine activity state (idle, moving, skilling, combat, dialogue).
- Summarize inventory, equipment, and resource counters.

### Output Contract
- Emit a normalized JSON snapshot with timestamp, client metadata, UI state, OCR, and derived state.
- Snapshot schema reference: `SNAPSHOT_SCHEMA.md`.
- Include confidence scores for key fields and a "stale" flag if capture is delayed.

## Hands (Action) Needs

### Input Interfaces
- Mouse move, click (down/up), drag, and scroll.
- Keyboard press, hold, and chorded inputs.
- Camera control (drag and key-based).

### Hardware Facing
- Enumerate input devices (mouse, keyboard) and record device metadata.
- Capture mouse DPI, polling rate, and acceleration settings when available.
- Support per-device behavior profiles and calibration.
- Detect display refresh rate and OS input latency where possible.

### Timing and Variability
- Configurable action timing distributions and jitter.
- Mouse pathing with curves and easing (no perfectly straight lines).
- Dwell time before click and after action completion.

### Safety Gates
- Pre-action validation: UI state matches expected targets.
- Abort or pause on unexpected UI changes or loss of focus.
- Dry-run mode that logs actions without execution.

### Outcome Validation
- Post-action checks to confirm expected UI or state changes.
- Retry logic with bounded attempts and backoff.
- Failure classification for auditing (missed click, blocked UI, wrong target).

## Logging and Observability
- Structured logs for each capture frame and each action attempt.
- Correlate action requests to pre-checks, inputs, and outcomes.
- Capture annotated screenshots for failed actions.

## Acceptance Criteria
- Snapshot schema is stable and validated against required fields.
- Average capture latency is measurable and within a configurable budget.
- Every action has a traceable audit record and outcome classification.

## Priority Queue (Hands and Eyes)
Legend: P0 = foundation, P1 = core, P2 = humanization, P3 = parity validation.
Dependency tags: dep:model, dep:mimicry, dep:none.

P0
- [ ] Client window discovery and focus tracking. (dep:none)
- [ ] Screen capture with FPS and ROI configuration. (dep:none)
- [ ] Snapshot schema definition and validation. (dep:none)
- [ ] Capture latency and dropped-frame metrics. (dep:none)
- [ ] Unified action API (move, click, drag, key, scroll). (dep:none)
- [ ] Pre-action UI validation gates and abort rules. (dep:none)
- [ ] Post-action verification with bounded retry and failure classification. (dep:none)
- [ ] Dry-run mode with action logging only. (dep:none)

P1
- [ ] OCR backend with pluggable providers and per-region confidence. (dep:none)
- [ ] UI element detector for core panels and tabs. (dep:none)
- [ ] Cursor state and hover text extraction. (dep:none)
- [ ] Minimap parsing for region inference. (dep:none)
- [ ] Focus recovery before any input execution. (dep:none)
- [ ] Expected model output schema for action intents and constraints. (dep:model)
- [ ] Human-in-the-loop approval toggle for unsafe actions. (dep:none)
- [ ] Hardware device enumeration for mouse/keyboard metadata. (dep:none)
- [ ] Device-level input profiles (DPI, polling, accel). (dep:mimicry)
- [ ] Detect display refresh rate and OS input latency. (dep:mimicry)

P2
- [ ] Mouse pathing with curve/easing presets. (dep:mimicry)
- [ ] Timing variance (dwell, jitter, reaction delay). (dep:mimicry)
- [ ] Drag actions with human-like start and end jitter. (dep:mimicry)
- [ ] Capture and annotate dataset tool. (dep:mimicry)
- [ ] Replay viewer for frame sequences and UI overlays. (dep:mimicry)

P3
- [ ] Define pass/fail acceptance criteria for perception parity. (dep:mimicry)
- [ ] Define pass/fail acceptance criteria for timing/motion parity. (dep:mimicry)
- [ ] Define pass/fail acceptance criteria for error and recovery parity. (dep:mimicry)
- [ ] Human session capture + annotation pipeline. (dep:mimicry)
- [ ] Replay-to-comparison harness (agent vs. human). (dep:mimicry)
- [ ] Calibration tooling to fit distributions to human baselines. (dep:mimicry)
- [ ] Reporting pipeline for parity results and regressions. (dep:mimicry)

## Active Queue (Top 10)
1) Implement screen capture with FPS and ROI configuration. (P0, dep:none) [done]
2) Track capture latency and dropped-frame metrics per session. (P0, dep:none) [done]
3) Define and validate the snapshot schema (JSON). (P0, dep:none) [done]
4) Build client window discovery and focus tracking. (P0, dep:none) [done]
5) Define a unified action API (move, click, drag, key, scroll). (P0, dep:none) [done]
6) Add pre-action UI validation gates and abort rules. (P0, dep:none) [done]
7) Add post-action verification with bounded retry and failure classification. (P0, dep:none) [done]
8) Implement dry-run mode with action logging only. (P0, dep:none) [done]
9) Add OCR backend with pluggable providers and per-region confidence scoring. (P1, dep:none) [done]
10) Create UI element detector for core panels and tabs. (P1, dep:none) [done]

## Active Queue (Next 5)
11) Add cursor state and hover text extraction. (P1, dep:none) [done]
12) Implement minimap parsing for region inference. (P1, dep:none) [done]
13) Add focus recovery before any input execution. (P1, dep:none) [done]
14) Define the expected model output schema for action intents and constraints. (P1, dep:model) [done]
15) Add human-in-the-loop approval toggle for unsafe actions. (P1, dep:none) [done]

## Active Queue (Next 5, Round 2)
16) Add hardware device enumeration for mouse/keyboard with metadata capture. (P1, dep:none) [done]
17) Add device-level input profiles (DPI, polling rate, accel) for timing modeling. (P1, dep:mimicry) [done]
18) Detect display refresh rate and OS input latency (where supported). (P1, dep:mimicry) [done]
19) Add mouse pathing with curve/easing presets. (P2, dep:mimicry) [done]
20) Add timing variance (dwell, jitter, reaction delay). (P2, dep:mimicry) [done]

## Active Queue (Next 5, Round 3)
21) Implement drag actions with human-like start and end jitter. (P2, dep:mimicry) [done]
22) Build a "capture and annotate" dataset tool. (P2, dep:mimicry) [done]
23) Add a replay viewer for frame sequences and UI overlays. (P2, dep:mimicry) [done]
24) Add action context logger for timing/motion features to enable tuning. (P2, dep:mimicry) [done]
25) Add per-session seed control for reproducible randomness in testing. (P2, dep:mimicry) [done]

## Active Queue (Next 5, Round 4)
26) Add hover dwell before click to simulate target acquisition. (P2, dep:mimicry) [done]
27) Add click down/up dwell variance and long-press support for drag actions. (P2, dep:mimicry) [done]
28) Add scroll wheel speed variance and pause patterns for scroll actions. (P2, dep:mimicry) [done]
29) Add misclick/near-miss modeling with corrective behavior (configurable rate). (P2, dep:mimicry) [done]
30) Add mouse acceleration profiles (DPI, OS speed, accel curve) with presets. (P2, dep:mimicry) [done]

## Active Queue (Next 5, Round 5)
31) Add target acquisition model (aim point selection within UI bounds). (P2, dep:mimicry) [done]
32) Add cursor settle behavior (brief stillness before final click). (P2, dep:mimicry) [done]
33) Add retry strategy for failed interactions (backoff, re-aim, re-try). (P2, dep:mimicry) [done]
34) Add action abort behavior when UI changes mid-action. (P2, dep:mimicry) [done]
35) Add UI scan patterns before actions (mouse sweep or hover checks). (P2, dep:mimicry) [done]

## Active Queue (Next 5, Round 6)
36) Add random-event detection from chat/notifications to suppress replies. (P2, dep:none) [done]

## Active Queue (Next 5, Round 7)
37) Add attention drift model that slightly biases cursor paths over time. (P2, dep:mimicry) [done]
38) Add cursor speed ramps (accelerate/decay rather than constant velocity). (P2, dep:mimicry) [done]
39) Add micro-tremor noise in slow cursor movements (sub-pixel jitter). (P2, dep:mimicry) [done]
40) Add edge avoidance for mouse paths (avoid perfectly straight to corners). (P2, dep:mimicry) [done]
41) Add randomized start point for mouse moves (from last idle position). (P2, dep:mimicry) [done]

## Active Queue (Next 5, Round 8)
42) Add probabilistic check of hover text before click. (P2, dep:mimicry) [done]
43) Add click targeting bias toward text center or icon center with drift. (P2, dep:mimicry) [done]
44) Add cursor settle behavior (brief stillness before final click) integration into action flow. (P2, dep:mimicry) [done]
45) Add probabilistic "double-check" loop for irreversible actions (drop, alch, trade). (P2, dep:mimicry) [done]
46) Add short thinking pauses after UI state changes. (P2, dep:mimicry) [done]

Notes:
- Cursor settle integration uses shared timing sampling; execution integration remains to wire into input executor.

## Active Queue (Next 5, Round 9)
47) Add action chaining variability (different orderings for equivalent steps). (P2, dep:mimicry) [done]
48) Add input burst modeling (short spurts followed by rest). (P2, dep:mimicry) [done]
49) Add session rhythm modeling (breaks, fatigue, time-based drift). (P2, dep:mimicry) [done]
50) Add context-based pacing (slow down in complex scenes, speed up in simple ones). (P2, dep:mimicry) [done]
51) Add action spacing based on in-game animations or cooldown cues. (P2, dep:mimicry) [done]

## Active Queue (Next 5, Round 10)
52) Add typing cadence modeling (key delays, bursts, corrections, backspace). (P2, dep:mimicry) [done]
53) Add keypress overlap modeling (shift+click timing variance). (P2, dep:mimicry) [done]
54) Add modifier key usage variance (shift, ctrl) where applicable. (P2, dep:mimicry) [done]
55) Add input device noise model (USB polling jitter, frame-time variance). (P2, dep:mimicry) [done]
56) Add handoff latency between mouse and keyboard actions. (P2, dep:mimicry) [done]

## Active Queue (Next 5, Round 11)
57) Add inter-action micro-pauses based on task complexity and recent activity. (P2, dep:mimicry) [done]
58) Add stochastic delay after action completion (human confirmation pause). (P2, dep:mimicry) [done]
59) Add reaction-time model (stimulus-to-action delay) with per-action distributions. (P2, dep:mimicry) [done]
60) Add context-specific click cadence presets (banking vs. skilling). (P2, dep:mimicry) [done]
61) Add session rhythm modeling (breaks, fatigue, time-based drift) integration. (P2, dep:mimicry) [done]

## Hands and Eyes Ticket Backlog

### Eyes
- [ ] Build client window discovery and focus tracking.
- [ ] Implement screen capture with FPS and ROI configuration.
- [ ] Add OCR backend with pluggable providers and confidence scoring.
- [ ] Create UI element detector for core panels and tabs.
- [ ] Implement minimap parsing for region inference.
- [ ] Add hover text and cursor state extraction.
- [ ] Define and validate the snapshot schema (JSON).
- [ ] Build a "capture and annotate" dataset tool.
- [ ] Add a replay viewer for frame sequences and UI overlays.

### Hands
- [ ] Define a unified action API (move, click, drag, key, scroll).
- [ ] Define the expected model output schema for action intents and constraints.
- [ ] Add mouse pathing with curve/easing presets.
- [ ] Add timing variance (dwell, jitter, reaction delay).
- [ ] Implement drag actions with human-like start and end jitter.
- [ ] Add focus recovery before any input execution.
- [ ] Add action gating with UI pre-checks and abort rules.
- [ ] Implement dry-run mode with action logging only.
- [ ] Add post-action verification and bounded retry logic.
- [ ] Add human-in-the-loop approval toggle for unsafe actions.

### Human-Equivalent Validation
- [ ] Define pass/fail acceptance criteria for perception parity.
- [ ] Define pass/fail acceptance criteria for timing/motion parity.
- [ ] Define pass/fail acceptance criteria for error and recovery parity.
- [ ] Build a human session capture + annotation pipeline.
- [ ] Build a replay-to-comparison harness (agent vs. human).
- [ ] Add calibration tooling to fit distributions to human baselines.
- [ ] Add a reporting pipeline for parity results and regressions.
