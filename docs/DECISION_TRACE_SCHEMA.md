# Decision Trace Schema

Purpose: define the JSONL format used in `logs/model_decisions.jsonl`.

## Entry Fields
- timestamp: string (ISO-8601)
- source: string
- message: string
- payload: object (Model Output Schema)

## Example
```json
{"timestamp":"2026-01-06T21:00:00Z","source":"plan","message":"plan next step","payload":{"decision_id":"dec_001","intent":"open_bank","confidence":0.78,"rationale":["inventory full"],"required_cues":["bank_chest_visible"],"risks":["misclick_near_npc"],"actions":[{"action_id":"act_001","action_type":"click","target":{"ui_element_id":"bank_chest","position":[960,540]},"confidence":0.72,"gating":{"verification_steps":["hover_text=Bank chest"],"abort_conditions":["modal_open"]}}]}}
```
