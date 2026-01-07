# Action Trace Schema

Purpose: define the JSONL schema for action execution logs in `logs/actions.jsonl`.

Each line is a JSON object with the fields below:

- `timestamp`: string (ISO-8601, UTC, with `Z` suffix)
- `intent`: object (ActionIntent)
  - `intent_id`: string
  - `action_type`: string (`move`, `click`, `drag`, `type`, `scroll`, `camera`)
  - `target`: object (target point/region or UI handle)
  - `confidence`: number (0.0 - 1.0)
  - `required_cues`: array of strings
  - `gating`: object (preconditions, e.g. `require_focus`)
  - `payload`: object (action-specific data, timing/motion hints)
- `result`: object (ActionResult)
  - `intent_id`: string
  - `success`: boolean
  - `failure_reason`: string
  - `details`: object (optional metadata)

Notes:
- Produced by `ActionLogger` in `src/actions.py`.
- `payload` may include `delay_ms`, `button`, `text`, `amount`, `timing`, or `motion` depending on action type.
