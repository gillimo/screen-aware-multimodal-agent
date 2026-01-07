# Execution Summary Schema

Purpose: define the schema for execution summaries written to `logs/execution_summary.json`.

Top-level fields:
- `timestamp`: string (ISO-8601, UTC, with `Z` suffix)
- `count`: integer
- `results`: array of objects

Result object fields:
- `intent_id`: string
- `success`: boolean
- `failure_reason`: string

Notes:
- Written by `cmd_decision_consume` and `cmd_decision_execute_file` in `src/app_cli.py`.
- `results` preserve execution order for the run.
