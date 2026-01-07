# Human-Like Toolchain Plan

Purpose: define the tools and interfaces needed for human-like perception, response, and input execution.

## Toolchain Layers

### 1) Perception and Stimulus Parity
- Screen capture with ROI extraction and frame timing metadata.
- Visual cue extraction: hover text, highlights, animation state, modal presence.
- Structured state merge: combine JSON state with visual cues into a single snapshot.
- Event stream: detect deltas between snapshots (new modal, chat line, action completion).

### 2) Response Modeling
- Reaction-time model: per-event latency distributions.
- Attention model: focus selection, re-checks, and task switching.
- Confidence gating: extra checks when uncertainty is high.
- Context pacing: align action timing with UI animations and cooldown cues.

### 3) Input Synthesis
- Mouse motion generator: curvature, acceleration, overshoot, micro-corrections.
- Click controller: down/up dwell, hover dwell, near-miss recovery.
- Keyboard controller: cadence, bursts, corrections, modifier timing.
- Camera controller: nudges, over-rotation, zoom pauses, corrective drags.

### 4) Session Rhythm
- Micro-pauses between actions.
- Burst and rest cycles.
- Long break scheduling and fatigue drift.

### 5) Safety and Policy Gates
- Opt-in execution toggle and rate limits.
- UI state verification before irreversible actions.
- Interrupt handling on unexpected UI changes.
- Comprehensive input and decision logging.

## Interfaces and Data Contracts
- InputProfile: timing distributions, error rates, motion parameters, session rhythm.
- StimulusSnapshot: merged visual + structured state with timestamps.
- ActionIntent: target, action type, confidence, required cues.
- ActionTrace: emitted input events with timing and outcome.

## Implementation Notes
- Support deterministic mode with seed control for testing.
- Provide preset profiles (subtle, normal, heavy) plus per-user customization.
- Log human-likeness metrics for calibration and benchmarking.

## Deliverables
- Tool interface definitions (schemas and enums).
- Core controllers (mouse, click, keyboard, camera).
- Calibration and evaluation harness tied to end-state benchmarks.

## Ticket Mapping (by layer)

Perception and Stimulus Parity
- Build screen capture pipeline with configurable FPS and region-of-interest support.
- Add visual cue extraction for animations, hover text, highlights, and overlays.
- Add structured-state augmentation pipeline (merge JSON state with visual cues).
- Add perception parity checks to ensure agent reacts to on-screen cues.
- Define stimulus parity requirements (visual cues vs. structured JSON inputs).

Response Modeling
- Add a reaction-time model (stimulus-to-action delay) with per-action distributions.
- Add focus checks (re-hover or re-read UI state) before committing actions.
- Add per-action confidence gating (extra checks when uncertainty is high).
- Add human-like pacing model tied to animation and UI feedback cues.

Input Synthesis
- Implement action executor interfaces (mouse move/click, keyboard input, camera control).
- Add non-linear mouse pathing (curves and easing) for mouse move actions.
- Add variable click timing (jitter and configurable distributions) for input actions.
- Add typing cadence modeling (key delays, bursts, corrections, backspace).
- Add human-like camera movement (short nudges, occasional over-rotation).

Session Rhythm
- Add session rhythm modeling (breaks, fatigue, time-based drift).
- Add inter-action micro-pauses based on task complexity and recent activity.
- Add input burst modeling (short spurts followed by rest).

Safety and Policy Gates
- Add a policy layer for allowed action types, rate limits, and cooldowns.
- Add a human-in-the-loop mode with step-by-step approval toggles.
- Add a sandbox action mode for dry runs that logs actions without executing them.
