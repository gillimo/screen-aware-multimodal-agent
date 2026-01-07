# Mimicry and Model Status

Purpose: track acceptance criteria status for Mimicry and Model.

Legend: done, partial, todo.

## Perception Parity (depends on Hands and Eyes)
- (partial) Screen snapshots include visual cues (hover text, highlights, animation states).
- (partial) Structured state is merged with visual cues into a unified snapshot.
- (done) Snapshot schema is validated and versioned.

## Response Modeling
- (todo) Reaction-time distributions are configurable per action type.
- (todo) Attention checks and confidence gates are enforced on uncertain actions.
- (todo) Context pacing aligns with animation/cooldown cues.

## Input Mimicry
- (todo) Mouse motion shows curvature, acceleration, overshoot, and correction.
- (todo) Click timing and dwell variance are within human-like ranges.
- (todo) Keyboard cadence includes burst/pauses and correction behavior.
- (todo) Camera movement includes nudges, over-rotation, and micro-adjustments.

## Session Rhythm
- (todo) Micro-pauses and burst/rest cycles are observable in traces.
- (todo) Long sessions show fatigue drift and pacing variation.

## Calibration and Evaluation
- (partial) Human-likeness scores compare agent traces to human baselines.
- (partial) Calibration workflow exists for fitting timing/motion distributions.
- (todo) Acceptance thresholds are defined and tracked over time.

## Safety and Auditability
- (partial) Every action has an intent, trace, and outcome record.
- (partial) Policy gates and interrupt handling are enforced.
