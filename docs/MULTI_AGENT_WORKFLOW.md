# Multi-Agent Workflow

Purpose: define how multiple agents coordinate work, handoffs, and logs.

## Roles
- Hands/Eyes: execution, perception, input timing, and local UI capture.
- Mimicry/Model: decision JSON, model prompts, validation, and KPI pipelines.
- Orchestrator (optional): decides sequencing and resolves conflicts.

## Handoff Points
- Snapshots: `data/snapshots/snapshot_latest.json` is the shared input.
- Decisions: `logs/model_decisions.jsonl` and `data/tutorial_decision.json` are shared outputs.
- Execution: `logs/actions.jsonl`, `logs/action_context.jsonl`, and `logs/execution_summary.json`.
- State: `data/tutorial_island_state.json` for progress and last execution.

## Coordination Rules
- Update `docs/HANDS_TALK.md` after each small task with a short note.
- Log work in `docs/LOGBOOK.md` with handle + date.
- Log bugs in `docs/BUG_LOG.md` before edits.
- Sync TODOs into `docs/TICKETS.md` when new tasks appear.
- Avoid overlapping file edits; claim a file in HANDS_TALK before large changes.

## Conflict Resolution
- If changes overlap, pause and discuss in HANDS_TALK.
- Prefer smallest viable change; avoid reverting unrelated edits.
- When unclear, add a note to `docs/QUESTION_LOG.md` and proceed with a safe fallback.

## Review Loop
- After a batch, update `docs/DOCS_CHECKLIST.md` and `docs/LOG_CHECKLIST.md`.
- Add a brief status recap in `docs/SIGNING_OFF.md` when closing a cycle.
