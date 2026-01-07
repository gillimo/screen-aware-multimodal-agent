# Audit Log Spec

Purpose: define audit log formats for decisions, actions, and KPI snapshots.

## Decisions
File: `logs/model_decisions.jsonl`
- timestamp: string (ISO-8601)
- source: string
- message: string
- payload: object (MODEL_OUTPUT_SCHEMA.md)

## Actions
File: `logs/actions.jsonl`
- timestamp: string (ISO-8601)
- intent: object (ActionIntent)
- result: object (ActionResult)
Schema: `ACTION_TRACE_SCHEMA.md`

## Action Context
File: `logs/action_context.jsonl`
- intent_id: string
- decision_id: string
- timing: object
- motion: object
Schema: `ACTION_CONTEXT_SCHEMA.md`

## Execution Summary
File: `logs/execution_summary.json`
- timestamp: string (ISO-8601)
- count: integer
- results: array
Schema: `EXECUTION_SUMMARY_SCHEMA.md`

## Human-Likeness KPI
File: `logs/human_kpi.jsonl`
- timestamp: string (ISO-8601)
- kpi: object (HUMAN_LIKENESS_KPI.md)

## Notes
- All logs are local by default.
- Use `decision-rotate` to archive decision logs.
