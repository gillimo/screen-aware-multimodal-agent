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
- `python run_app.py capture --fps 2 --seconds 5 --roi data/roi.json` to emit a session report.
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
- `python run_app.py kpi-append --kpi data/human_kpi.json --out logs/human_kpi.jsonl` to append KPI log.
- `python run_app.py purge-decisions --days 30` to prune old decision logs.

## OSRS Client Overlay (Planned)
- Primary UI surface is a silent overlay attached to the OSRS original client.
- Until the overlay ships, use `python run_app.py gui` for planning and control.

## Data Sources
- Local JSON in `data/` is the source of truth.

## Action Execution (Optional)
- Enable only when policy constraints are configured.
- Use human-like input settings for timing, motion, and pacing.

## Logging
- Record changes in `docs/LOGBOOK.md` with handle + date.
- Log bugs in `docs/BUG_LOG.md` before code edits.

## Git Workflow (Local Commits)
- Check status before edits: `git status`.
- Commit locally with a clear message: `git commit -am "message"`.
- Keep commits scoped to a single topic when possible.

### Commit Message Conventions
- Use imperative mood (e.g., "Add schema validation").
- Include a short scope when helpful (e.g., "mimicry: add KPI schema").
- Avoid multi-topic commits.
