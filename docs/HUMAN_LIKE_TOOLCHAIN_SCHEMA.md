# Human-Like Toolchain Schema

Purpose: define data contracts for perception, intent, and input traces.

Related schemas: `SNAPSHOT_SCHEMA.md`, `STATE_SCHEMA.md`.

## InputProfile
Defines timing, motion, and variability parameters for human-like input.

Fields
- profile_id: string
- timing: object
  - reaction_ms: { mean, stdev, min, max }
  - click_ms: { down_up_mean, down_up_stdev }
  - inter_action_ms: { mean, stdev }
- motion: object
  - curve_strength: number
  - accel_profile: string (linear, ease_in, ease_out, ease_in_out)
  - overshoot_rate: number
  - micro_jitter_px: number
- errors: object
  - misclick_rate: number
  - correction_rate: number
- session: object
  - burst_mean_actions: number
  - rest_mean_ms: number
  - fatigue_drift_rate: number
- device: object
  - polling_jitter_ms: number
  - dpi_profile: string

## StimulusSnapshot
Merged structured JSON and visual cues for a single moment.

Fields
- timestamp: string (ISO-8601)
- session_id: string
- client: object (window bounds, focus, scale)
- roi: object (named regions and bounds)
- ui: object (open interfaces, hover text, selection)
- ocr: array (bbox, text)
- cues: object
  - animation_state: string
  - highlight_state: string
  - modal_state: string
  - hover_text: string
- derived: object (location, activity, combat)
- account: object (stats, inventory, equipment)

## StimulusDelta
Event-like changes between snapshots.

Fields
- timestamp: string (ISO-8601)
- type: string (chat_line, modal_open, action_complete, inventory_change)
- details: object

## ActionIntent
Declarative intent before input generation.

Fields
- intent_id: string
- action_type: string (move, click, drag, type, camera)
- target: object (ui_element_id, position, bounds)
- confidence: number
- required_cues: array (strings)
- gating: object (verification_steps, abort_conditions)

## ActionTrace
Observed inputs and outcomes for auditing and tuning.

Fields
- intent_id: string
- inputs: array (type, timestamp, x, y, key)
- timings: object (reaction_ms, action_ms, dwell_ms)
- outcome: object (success, failure_reason)
- snapshot_before: string (reference id)
- snapshot_after: string (reference id)

## PlannerDecision
Structured output from the planner to the executor.

Fields
- decision_id: string
- intent: string
- target: object (optional)
- rationale: array of strings
- required_cues: array
- risks: array
- confidence: number
