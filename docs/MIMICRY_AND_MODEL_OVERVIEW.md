# Mimicry and Model Overview

Purpose: consolidated view of Mimicry and Model scope, tickets, schemas, and dependencies.

## Scope
- Human-like perception parity and response modeling.
- Input synthesis (mouse, click, keyboard, camera).
- Session rhythm and pacing.
- Calibration, evaluation, and acceptance criteria.

## Core Docs
- Goals: `HUMAN_LIKE_GOALS.md`
- Behavior catalog: `HUMAN_LIKE_BEHAVIOR_CATALOG.md`
- Toolchain plan: `HUMAN_LIKE_TOOLCHAIN_PLAN.md`
- Toolchain schema: `HUMAN_LIKE_TOOLCHAIN_SCHEMA.md`
- Acceptance checklist: `MIMICRY_AND_MODEL_ACCEPTANCE.md`
- Schema index: `SCHEMAS.md`

## Key Schemas
- State: `STATE_SCHEMA.md`
- Snapshot: `SNAPSHOT_SCHEMA.md`
- Toolchain interfaces: `HUMAN_LIKE_TOOLCHAIN_SCHEMA.md`

## Dependencies on Hands and Eyes
- Screen capture with ROI and timing metadata.
- OCR and UI element detection for hover text and highlights.
- Animation state extraction and cue tracking.
- Snapshot emission and schema validation.

## Ticket Clusters (by module)
- Perception parity: visual cue extraction, structured state merge, parity checks.
- Response modeling: reaction-time distributions, confidence gates, pacing tied to cues.
- Input synthesis: motion curves, click dwell, keyboard cadence, camera behaviors.
- Session rhythm: micro-pauses, burst/rest cycles, fatigue drift.
- Evaluation: human-likeness scoring, calibration workflow, acceptance thresholds.
- Schema and validation: state/snapshot schemas and validation in CLI/pipeline.
