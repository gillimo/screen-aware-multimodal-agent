# Snapshot Schema (Screen-Aware Inputs)

Purpose: define the normalized JSON snapshot emitted by perception.

## Required Top-Level Fields
- capture_id: string
- timestamp: string (ISO-8601)
- version: number
- stale: boolean
- session_id: string
- client: object
- roi: object
- ui: object
- ocr: array
- cues: object
- derived: object
- account: object

## client
- window_title: string
- bounds: object (x, y, width, height)
- focused: boolean
- scale: number
- fps: number
- capture_latency_ms: number

## roi
- Named regions with bounds (minimap, chatbox, inventory, etc).

## ui
- open_interface: string
- selected_tab: string
- cursor_state: string
- hover_text: string
- elements: array (id, type, label, state, bounds)
- dialogue_options: array

## ocr
- entries: array (bbox, text, confidence)

## cues
- animation_state: string
- highlight_state: string
- modal_state: string
- hover_text: string
- chat_prompt: string (e.g., "continue")

## derived
- location: object (region, subarea, coordinates optional)
- activity: object (type, state, progress)
- combat: object (state)

## account
- name: string
- membership_status: string
- skills: object
- inventory: array
- equipment: object
- resources: object

## ocr_metadata
- inventory_lines: array
- tooltips: array

## Example
```json
{
  "timestamp": "2026-01-06T21:00:00Z",
  "session_id": "sess_001",
  "client": {
    "window_title": "Old School RuneScape",
    "bounds": { "x": 0, "y": 0, "width": 1920, "height": 1080 },
    "focused": true,
    "scale": 1.0,
    "fps": 20,
    "capture_latency_ms": 18
  },
  "roi": {
    "minimap": { "x": 1700, "y": 40, "width": 200, "height": 200 }
  },
  "ui": {
    "open_interface": "none",
    "selected_tab": "inventory",
    "cursor_state": "interact",
    "hover_text": "Chop down Tree",
    "elements": [],
    "dialogue_options": []
  },
  "ocr": [
    { "bbox": [12, 834, 240, 860], "text": "You chop the tree.", "confidence": 0.92 }
  ],
  "cues": {
    "animation_state": "active",
    "highlight_state": "none",
    "modal_state": "none",
    "hover_text": "Chop down Tree"
  },
  "derived": {
    "location": { "region": "Lumbridge", "subarea": "South trees" },
    "activity": { "type": "woodcutting", "state": "active", "progress": 0.4 },
    "combat": { "state": "out_of_combat" }
  },
  "account": {
    "name": "gillimo",
    "membership_status": "f2p",
    "skills": { "woodcutting": 15 },
    "inventory": [ "Bronze axe", "Logs x12" ],
    "equipment": { "weapon": "Bronze axe" },
    "resources": { "gp": 1200 }
  }
}
```
