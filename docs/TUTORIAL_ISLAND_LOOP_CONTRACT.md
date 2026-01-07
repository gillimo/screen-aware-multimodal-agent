# Tutorial Island Loop Contract

Purpose: define the JSON-only handoff between state snapshots and decision output.

## Inputs
- Snapshot JSON: see `SNAPSHOT_SCHEMA.md`.
- Tutorial state JSON: `data/tutorial_island_state.json`.
- Phase decisions: `data/tutorial_island_decisions.json`.

Fullscreen assumption: the OSRS client runs fullscreen for consistent bounds and ROI.

## Output
- Decision JSON: must match `MODEL_OUTPUT_SCHEMA.md`.

## Loop
1) Read latest snapshot JSON.
2) Read tutorial state (phase + step).
3) Select a decision template for the phase.
4) Validate decision output schema.
5) Emit decision JSON to stdout or file.
6) External executor applies changes and writes a new snapshot + updated tutorial state.

CLI shortcut: `python run_app.py go --snapshot data/snapshots/snapshot_latest.json --out data/tutorial_decision.json`.
`go` now chains decision logging, `decision-execute`, and snapshot capture in one call.

## State Updates
- Update `phase` and `step` when objectives are met.
- Append completed step IDs to `completed`.
- Add required cues to `required_cues` before advancing.
- Track `repeat_count` and `decision_index` to avoid repeating a stuck decision when cues are missing or snapshots are stale.
