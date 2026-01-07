# Mimicry and Model Acceptance Checklist

Purpose: define end-state acceptance criteria for the Mimicry and Model workstream.

## Acceptance Criteria

### Perception Parity (depends on Hands and Eyes)
- Screen snapshots include visual cues (hover text, highlights, animation states).
- Structured state is merged with visual cues into a unified snapshot.
- Snapshot schema is validated and versioned.

### Response Modeling
- Reaction-time distributions are configurable per action type.
- Attention checks and confidence gates are enforced on uncertain actions.
- Context pacing aligns with animation/cooldown cues.

### Input Mimicry
- Mouse motion shows curvature, acceleration, overshoot, and correction.
- Click timing and dwell variance are within human-like ranges.
- Keyboard cadence includes burst/pauses and correction behavior.
- Camera movement includes nudges, over-rotation, and micro-adjustments.

### Session Rhythm
- Micro-pauses and burst/rest cycles are observable in traces.
- Long sessions show fatigue drift and pacing variation.

### Calibration and Evaluation
- Human-likeness scores compare agent traces to human baselines.
- Calibration workflow exists for fitting timing/motion distributions.
- Acceptance thresholds are defined and tracked over time.

### Safety and Auditability
- Every action has an intent, trace, and outcome record.
- Policy gates and interrupt handling are enforced.

## Dependencies (Hands and Eyes)
- Screen capture with ROI and timing metadata.
- OCR and UI element detection for hover text and highlights.
- Animation state extraction and cue tracking.
- Snapshot emission and schema validation.
