# How To Operate (AgentOSRS)

This project provides planning and analysis for OSRS, with optional action execution when explicitly enabled.

## Reference Order
1) `PERMISSIONS.md`
2) This file
3) `CAPABILITIES.md`
4) `DEPENDENCIES.md`
5) `METRICS.md`
6) `PROJECT_VISION.md`
7) `TICKETS.md` / `BUG_LOG.md`
8) `SIGNING_OFF.md`

## Hands and Eyes Backlog
- Use `HANDS_AND_EYES.md` for perception/action requirements and focused tickets.
- When adding new hands/eyes items, log them there first, then sync key items into `TICKETS.md`.

## CLI Flow
- `python run_app.py status` to see the current snapshot.
- `python run_app.py plan` to generate a next-steps plan.
- `python run_app.py plan --model-message "plan next step"` to generate a model-driven plan.
- `python run_app.py ratings` to view ratings.
- `python run_app.py quests` for quest guidance.
- `python run_app.py readiness` for boss readiness.
- `python run_app.py gui` to open the GUI.
- `python run_app.py capture --title "Old School RuneScape"` to emit a snapshot stub.
- `python run_app.py capture --fps 2 --seconds 5 --roi data/roi.json` to emit a session report with ROI presets.
- `python run_app.py validate --snapshot data/snapshots/example.json` to validate a snapshot file.
- `python run_app.py validate` to validate schemas (optional `--snapshot path`).
- `python run_app.py validate-snapshot --snapshot path` to validate a snapshot only.
- `python run_app.py model --message "hello"` to query the local model.
- `python run_app.py model --message "reply" --chat-log data/chat.txt` to suppress replies on random events.
- `python run_app.py model-decision --message "plan next step"` to emit decision JSON.
- `python run_app.py profiles` to list humanization profiles.
- `python run_app.py profiles --profile subtle` to view a profile.
- `python run_app.py profile-select --profile normal` to set the active profile.
- `python run_app.py validate-profiles` to validate humanization profiles.
- `python run_app.py validate-model-output --model-output path` to validate model output JSON.
- `python run_app.py score-human --traces path` to score traces (stub).
- `python run_app.py score-human-write --traces path --out data/human_kpi.json` to write KPI output.
- `python run_app.py validate-kpi --kpi data/human_kpi.json` to validate KPI output.
- `python run_app.py validate-decision-trace --trace-path path` to validate decision logs.
- `python run_app.py decision-replay --trace-path path` to list decisions from logs.
- `python run_app.py decision-summary --trace-path path --out data/decision_summary.json` to export decision summary.
- `python run_app.py decision-tail --trace-path path --limit 10` to show recent decisions.
- `python run_app.py decision-export --trace-path path --out logs/model_decisions.jsonl.gz` to export decisions.
- `python run_app.py decision-consume --trace-path logs/model_decisions.jsonl` to load the latest decision actions.
- `python run_app.py decision-execute --trace-path logs/model_decisions.jsonl` to execute the latest decision actions (live input).
- `python run_app.py decision-execute --trace-path logs/model_decisions.jsonl --dry-run` to verify actions without input execution.
- `python run_app.py decision-execute-file --model-output data/tutorial_decision.json` to execute a decision JSON file.
- `python run_app.py decision-execute-file --model-output data/tutorial_decision.json --dry-run` to verify a decision file without input execution.
- `python run_app.py decision-execute --trace-path logs/model_decisions.jsonl --max-actions 2` to limit execution to a few intents.
- `python run_app.py decision-execute --trace-path logs/model_decisions.jsonl --seed 123` to force deterministic randomness for testing.
- `python run_app.py decision-view --trace-path path --limit 20` to view recent decisions with timestamps.
- `python run_app.py decision-rotate --trace-path logs/model_decisions.jsonl --out-dir logs/archive` to rotate logs.
- `python run_app.py kpi-append --kpi data/human_kpi.json --out logs/human_kpi.jsonl` to append KPI log.
- `python run_app.py tutorial-loop --snapshot data/snapshots/snapshot_latest.json --out data/tutorial_decision.json` to emit tutorial decisions.
- `python run_app.py go --snapshot data/snapshots/snapshot_latest.json --out data/tutorial_decision.json` to generate a decision, execute it, and capture a new snapshot (requires an active profile).
- `python run_app.py go --out data/tutorial_decision.json --max-actions 1 --sleep-ms 250` to run a minimal, paced `go`.
- `python run_app.py go --seed 123 --max-actions 2` to run deterministic input timing for reproducible tests.
- `python run_app.py go --out data/tutorial_decision.json --trace-path logs/model_decisions.jsonl` to log decisions to a specific trace file.
- `python run_app.py purge-decisions --days 30` to prune old decision logs.
- `python scripts/score_mimicry.py --run-id test --scenario tutorial` to score the mimicry rubric from logs.

## OSRS Client Overlay (Planned)
- Primary UI surface is a silent overlay attached to the OSRS original client.
- Until the overlay ships, use `python run_app.py gui` for planning and control.

## Data Sources
- Local JSON in `data/` is the source of truth.

## Action Execution (Optional)
- Enable only when policy constraints are configured.
- Use human-like input settings for timing, motion, and pacing.
- Retry/backoff can be configured per intent (`payload.retry`) or profile (`retry`).
- Action policy config lives at `data/action_policy.json` (allowed/denied actions, rate limits).
- Execution will pause if snapshot chat lines indicate a random event.
- Press `Esc` in the console to abort a running execution loop.

## Human-Like Execution Notes
- Live clicks apply a short settle delay and click dwell based on the active humanization profile.
- Mouse moves use non-linear paths with micro-jitter from the active profile.
- Live clicks may include a rare misclick with an automatic correction.
- Inter-action pacing uses profile timing/session settings with spacing between actions.
- Hover dwell before click simulates target acquisition (profile-driven).
- Click execution respects UI focus/hover gating when snapshot data is provided.
- Clicks use variable down/up dwell and optional multi-click gaps (profile-driven).
- Scrolls use stepwise variance with brief pauses to avoid robotic pacing.
- Mouse moves may overshoot slightly with corrective micro-moves (profile-driven).
- Mouse paths avoid screen edges and jitter the start position to reduce robotic motion.
- Mouse paths use speed ramps (accelerate/decay) instead of constant velocity.
- Execution aborts remaining actions if the snapshot shows a UI/modal change mid-run.
- Low-confidence actions add a short confirmation pause and may be skipped if hover text is missing.
- UI changes trigger a brief "thinking" pause before aborting remaining actions.
- Irreversible actions (drop/alch/trade) insert a double-check pause and verify hover text when available.
- Unexpected modals or UI states trigger an interrupt pause before continuing.
- Camera actions use nudges/over-rotation and zoom pauses for human-like movement.
- Session fatigue drift adds small delays as action count grows.
- Input bursts insert occasional longer rests between action clusters.
- Equivalent action steps may run in a slightly shuffled order to avoid repetition.
- Clicks sometimes re-check hover text before committing to reduce robotic behavior.
- Cursor paths drift slightly over time to avoid a static signature.
- Targets are re-aimed if the snapshot suggests the viewport shifted.
- Occluded UI elements trigger a short wait before skipping the action.
- Click cadence adapts by context (banking vs skilling) when provided.
- Click targets can bias toward text/icon centers with minor drift.
- Failed actions may retry with a small re-aim offset before backing off.
- Panic pauses trigger on suspicious chat/trade keywords before proceeding.
- Idle behaviors include edge pauses, offscreen cursor travel, UI scans, and occasional tab toggles.
- Focus recovery clicks back into the client when snapshots report lost focus.
- Camera drags can vary slightly in direction to avoid repeated patterns.
- Use `profile-select` to switch between subtle/normal/heavy behavior curves.

## Logging
- Record changes in `docs/LOGBOOK.md` with handle + date.
- Log bugs in `docs/BUG_LOG.md` before code edits.
- Execution summaries are written to `logs/execution_summary.json` after decision execution.

## Git Workflow (Local Commits)
- Check status before edits: `git status`.
- Commit locally with a clear message: `git commit -am "message"`.
- Keep commits scoped to a single topic when possible.

### Commit Message Conventions
- Use imperative mood (e.g., "Add schema validation").
- Include a short scope when helpful (e.g., "mimicry: add KPI schema").
- Avoid multi-topic commits.
