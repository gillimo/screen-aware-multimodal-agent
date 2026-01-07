# Tutorial Island Milestone

Purpose: define the milestone plan to fully automate Tutorial Island as the first end-to-end goal.

## Goal
Complete Tutorial Island from new account start to mainland arrival with human-like input and full logging.

## Scope
- End-to-end autonomy for Tutorial Island only.
- Uses local model for decisions and action intents.
- Human-like input profiles enforced for all actions.
- Full decision, action, and KPI logging.

## Phases
1) Perception readiness (Hands and Eyes).
2) Action execution readiness (Hands and Eyes + Mimicry).
3) Decision loop and state tracking (Mimicry/Model).
4) Full run with replay and KPI review.

## Required Capabilities
### Perception (Hands and Eyes)
- Reliable window focus, capture, ROI, and latency metrics.
- Cursor state, hover text, dialogue, and UI element detection.
- Minimap location inference and activity detection.
- Snapshot schema validation and cue extraction.

### Action Execution (Hands and Eyes + Mimicry)
- Mouse movement with curvature, jitter, overshoot, and correction.
- Click timing variance and drag support.
- Keyboard typing cadence and modifier timing.
- Focus recovery and action gating.
- Retry logic with safe abort rules.

### Decision and Memory (Mimicry/Model)
- Model output schema enforcement and strict JSON policy.
- Decision logging and trace validation.
- KPI scoring and logging per session.
- Humanization profile selection and enforcement.
- Tutorial state write-back with last decision + execution summary.

## Acceptance Criteria
- Complete run without manual intervention.
- No invalid actions outside allowed policy gates.
- Human-like KPI within defined thresholds.
- Full logs available: decisions, actions, KPI, snapshots.

## Dependencies
- Hands and Eyes implementation tickets for capture, OCR, UI detection, and execution.
- Mimicry/Model tickets for model decision enforcement, KPI pipelines, and logging.
