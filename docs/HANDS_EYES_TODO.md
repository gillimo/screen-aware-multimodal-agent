# Hands/Eyes Remaining Work TODO

Purpose: consolidated, actionable checklist for remaining hands/eyes work.

## Execution Loop (Go Orchestration)
- [x] Wire `go` to: capture snapshot_latest -> consume decision JSON -> execute -> capture new snapshot (manual run pending).
- [x] Add `--dry-run` option to `decision-execute-file` for safe verification.
- [x] Add executor status output JSON (success, failure_reason, timestamps).
- [x] Add execution result write-back (optional) to `data/tutorial_island_state.json`.
- [x] Add retry policy hooks (re-aim, wait, retry) in executor loop.
- [x] Add `--dry-run` support to `go` command (propagate flag).
- [x] Add `--trace-path` override for `go` execution output log.
- [x] Emit `logs/execution_summary.json` per `go` invocation.
- [x] Capture pre-action snapshot_latest before decision execution.
- [x] Capture post-action snapshot_latest after execution completes.
- [x] Add `--max-actions` guard for `go` (limit intents).
- [x] Add `--sleep-ms` between `go` stages (debug safety).

## Perception Pipeline (Real Capture -> State)
- [x] Integrate OCR provider into snapshot build (chat, tooltips, UI labels).
- [x] Integrate UI detector into snapshot build (tabs, buttons, slots).
- [x] Add cursor state and hover text extraction from capture.
- [x] Add minimap parsing for location inference beyond stub.
- [x] Add ROI definitions and capture config in `data/roi.json`.
- [x] Add snapshot versioning and `stale` flag on delayed capture.
- [x] Add snapshot `capture_id` for correlating action traces.
- [x] Add `capture_latency_ms` to snapshot stub when available.
- [x] Add `client.focused` sampling to snapshot build.
- [x] Add hover text OCR pipeline and attach to `ui.hover_text`.
- [x] Add dialogue option OCR to `ui.dialogue_options`.
- [x] Add inventory slot OCR metadata (count, labels).
- [x] Add minimap-derived `derived.location` fields.
- [x] Add OCR region map file (`data/ocr_regions.json`) for chat/tooltips.
- [x] Add UI detector config file (`data/ui_detector_regions.json`) for tabs/buttons.
- [x] Add snapshot sanitizer for stale/partial OCR output.
- [x] Add ROI presets for fixed, resizable, fullscreen clients.
- [x] Add perception region maps doc for OCR/UI region configs.

## Action Execution Enhancements
- [x] Use mouse pathing curve + speed ramps in live executor.
- [x] Apply timing profile (hover dwell, settle, click pressure).
- [x] Apply misclick/near-miss and corrective behavior in executor.
- [x] Apply drag start hesitation + end jitter in executor.
- [x] Apply input noise (polling/frame jitter) in executor.
- [x] Apply pacing/spacing based on cues in executor loop.
- [x] Apply focus checks and re-hover checks before click (if enabled).
- [x] Apply attention drift and edge avoidance on targets.
- [x] Add action-level `cooldown_ms` support from profile.
- [x] Add click pressure variance in `input_exec.click`.
- [x] Add per-action `max_retries` and backoff config.
- [x] Add `camera` action handling for drag + scroll variants.
- [x] Add `scroll` easing for shorter bursts and pauses.
- [x] Add `type` cadence from profile (per-char jitter).
- [x] Add `hover_dwell_ms` default from profile if missing.
- [x] Add `settle_ms` jitter override per profile/session config.
- [x] Add click double-confirm guard for irreversible actions.
- [x] Add optional `rehover` check before click for low confidence.

## Safety + Policy (Optional)
- [x] Add policy config file for allowed actions, rate limits, cooldowns.
- [x] Add opt-in safety gates toggle (disabled by default per request).
- [x] Add interrupt handling integration with pause/resume strategy.
- [x] Add `ApprovalPolicy` config toggle in `data/local_model.json`.
- [x] Add `require_focus` gate default in profile/settings.
- [x] Add `random_event` chat detection guard in execution loop.
- [x] Add action denylist override for high-risk actions.
- [x] Add explicit abort reasons to `logs/actions.jsonl` when gated.

## Mimicry Evaluation (P3)
- [x] Define acceptance thresholds file for parity criteria.
- [x] Build trace capture for agent sessions (input traces).
- [x] Build trace comparison report with pass/fail flags.
- [x] Add regression report diffing (previous vs current).
- [x] Add `scripts/compare_traces.py` integration with report output path.
- [x] Add `scripts/human_equivalence_report.py` CLI help text.
- [x] Add evaluator config file (`data/human_equivalence_thresholds.json`).

## Logging + Audit
- [x] Add action trace schema doc for `logs/actions.jsonl`.
- [x] Add context trace schema doc for `logs/action_context.jsonl`.
- [x] Add execution summary JSON in `logs/execution_summary.json`.
- [x] Add execution summary entry to `docs/LOG_CHECKLIST.md`.
- [x] Add action/context schema refs to `docs/LOG_CHECKLIST.md`.
- [x] Add action/context schema refs to `docs/DOCS_CHECKLIST.md`.
- [x] Add execution summary schema link to `docs/SCHEMAS.md`.

## Tutorial Island Execution
- [x] Align decision JSON with executor target resolution (coords vs ui IDs).
- [x] Implement minimal decision templates for first 3 tutorial steps.
- [x] End-to-end run: snapshot -> decision -> execute -> snapshot (wired in go; manual run pending).
- [x] Add `data/tutorial_decision.json` validation against schema.
- [x] Add tutorial decision examples for first room (chat + move).
- [x] Add tutorial decision for camera rotate + zoom step.
