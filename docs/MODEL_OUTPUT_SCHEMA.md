# Model Output Schema (Action Intents)

Purpose: define the expected JSON output for model-generated action intents.

## ActionIntent
- intent_id: string
- action_type: string (move, click, drag, type, scroll, camera)
- target: object (ui_element_id, position, bounds)
- confidence: number (0-1)
- required_cues: array (strings)
- gating: object (pre/post checks, abort rules)
- payload: object (action-specific fields)

## Output Envelope (Optional)
```json
{
  "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
  "session_id": "string",
  "intents": [
    {
      "intent_id": "intent_001",
      "action_type": "click",
      "target": { "x": 100, "y": 200 },
      "confidence": 0.92,
      "required_cues": [ "hover_text" ],
      "gating": { "require_focus": true },
      "payload": {}
    }
  ]
}
```
