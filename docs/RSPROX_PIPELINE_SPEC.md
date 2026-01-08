# RSProx-First Pipeline Spec

Purpose: define the fast-path automation pipeline that treats RSProx as the primary state source, with optional heavy perception only when needed.

## Goals
- Minimize per-tick latency on the hot path.
- Keep a single normalized state object for model + executor.
- Defer expensive OCR/snapshot work to recovery or validation steps.
- Preserve auditability with clear logging boundaries.

## Pipeline Stages (Hot Path)
1) Ingest RSProx state (HTTP).
2) Normalize into canonical state object (minimal contract).
3) Build model prompt/context from normalized state.
4) Model emits JSON action intents (`MODEL_OUTPUT_SCHEMA.md`).
5) Validate intents and log decision trace.
6) Execute intents with policy gating and action context logging.
7) Capture lightweight post-action state from RSProx.
8) Verify outcomes (fast checks).

## Optional Enrichment (Fallback Path)
Trigger when any of these conditions are met:
- Stuck detection (no state progress for N ticks).
- Low-confidence decision or failed post-action verification.
- Inconsistent or stale RSProx state.
- Focus lost or UI modal uncertainty.

Fallback steps:
1) Capture full snapshot (screen + OCR).
2) Merge enrichment into normalized state.
3) Re-evaluate decision or recovery action.
4) Log fallback reason + artifacts.

## Timing Budgets (Target)
- RSProx fetch + normalize: < 40ms
- Model decision: < 200ms (local LLM target)
- Intent validation + logging: < 20ms
- Execution pre-checks: < 30ms
- Post-action RSProx verify: < 40ms
- Fallback capture (only on demand): best effort, not in hot path

## Normalized State (Minimal Contract)
The normalized state should be sufficient for:
- Model prompt construction
- Policy gating and execution checks
- Post-action verification

The exact fields are defined in the normalization contract (to be specified in tickets). Avoid heavy OCR fields on the hot path unless required.

## Logging Boundaries
Always-on (hot path):
- Decision trace (model output, validation results)
- Action execution summary (intent id, result)
- Minimal timing metrics per stage

Fallback-only:
- Full snapshot payloads
- OCR results and screenshots
- Detailed verification diffs

## Notes
- Canonical loop stays JSON action-intent based (`CORE_LOOP.md`).
- Free-text command loops remain test-only.

## Appendix: Normalization Contract (Draft)

Purpose: define the minimal, fast normalized state that the model + executor consume on the hot path.

### Contract Principles
- Minimal: only fields required for decisions, gating, and verification.
- Stable: versioned and backward-compatible.
- Fast: zero OCR dependencies on hot path.
- Enrichable: optional fields can be attached later without breaking consumers.

### Required Sections (Hot Path)
- `meta`: timestamps, source (`rsprox`), freshness.
- `client`: focus state and bounds (execution gating).
- `ui`: open interface id, dialogue state, hover text (if available).
- `cues`: modal state, animation state, chat prompt (if available).
- `state`: player position, stats (hp), inventory summary, nearby NPCs.

### Optional Enrichment (Fallback)
- `ocr`: full OCR payload from screen capture.
- `ui_elements`: bounding boxes and labels from UI detection.
- `images`: references to saved screenshots or crops.
- `derived`: location inference, activity inference, combat inference.

### Versioning
- `meta.schema_version` increments on breaking changes.
- Consumers must ignore unknown fields.

### Mapping Notes
- RSProx fields map directly into `state` and `cues` where possible.
- UI/hover text may remain empty on hot path unless provided by another source.
