# Human-Likeness KPI Log

Purpose: define the JSONL log format for stored KPI entries.

## Entry Fields
- timestamp: string (ISO-8601)
- kpi: object (HUMAN_LIKENESS_KPI.md)

## Example
```json
{"timestamp":"2026-01-06T21:00:00Z","kpi":{"total_events":120,"unique_action_types":6,"reaction_ms_avg":240.5,"notes":"stub scorer; replace with calibrated metrics"}}
```
