# State Awareness Requirements (AgentOSRS)

This document defines the full set of signals and structured JSON the local model would need to react and act responsibly. It is intended as a handoff spec for a screen-aware agent that operates with F2P constraints.

## Goals
- Identify where we are, what we can do, and what we see.
- Normalize OSRS client state into a consistent JSON snapshot.
- Provide enough context for short/medium/long-term planning.
- Preserve a clear boundary: observation and decision signals are explicit and auditable.

## Input Signals (Capture Layer)

### Window/Client
- window_title
- window_bounds (x, y, width, height)
- window_focus (focused/unfocused)
- client_scale (in-game scaling)
- fps (capture rate)
- capture_latency_ms

### Regions of Interest (ROI)
- minimap
- chatbox
- inventory
- equipment
- stats/skills tab
- quest tab
- prayer tab
- spellbook
- settings
- bank interface
- shop interface
- dialogue box
- world map

### Visual Detection
- UI elements (buttons, tabs, icons, slots)
- interactable objects (NPCs, objects, ground items)
- cursor state (default, interact, attack, use)
- hover tooltip text
- selection highlight (selected item/spell)
- animation state (idle, active, cooldown)

### OCR Text
- chat lines
- system messages
- dialogue text
- hover tooltips
- interface labels
- inventory item names (when visible)

## Derived State (Understanding Layer)

### Location
- region name (e.g., Lumbridge)
- sub-area hint (e.g., Lumbridge bank)
- approximate coordinates (if inferable)
- nearest landmarks (bank, furnace, anvil, altar)

### Activity Context
- current action (idle, moving, skilling, dialogue, combat)
- action progress (percent or time remaining)
- combat state (in combat, out of combat, danger)
- resource targets (tree, fishing spot, ore vein)
- animation cue timing (start/end, interruptible)

### Account State
- account name
- skill levels (F2P-relevant)
- quest completion (F2P list)
- equipment loadout
- inventory summary
- gp/currency count
- weight/energy

### UI State
- open interface (bank, shop, crafting, etc)
- selected tab
- open dialogue options
- scroll position (where applicable)
- notifications (level up, quest complete)

## Planning Inputs (Decision Layer)

### Constraints
- membership_status: "f2p"
- risk tolerance (low/medium/high)
- time budget
- allowed zones (safe/unsafe)
- preferred activities (skilling, questing, combat)

### Objectives
- preset name (e.g., make_best_money_f2p)
- short-term steps
- medium-term milestones
- long-term goals

### Knowledge Store
- F2P method catalog (skill, gp/hour, xp/hour, requirements)
- Quest dependency graph (F2P)
- Item requirements per method
- Training thresholds (level gates)
- Travel routes (safe paths)

## JSON Snapshot (Example)
```json
{
  "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
  "session_id": "string",
  "client": {
    "window_title": "Old School RuneScape",
    "bounds": { "x": 0, "y": 0, "width": 1920, "height": 1080 },
    "focused": true,
    "scale": 1.0
  },
  "roi": {
    "minimap": { "x": 1700, "y": 40, "width": 200, "height": 200 },
    "chatbox": { "x": 0, "y": 820, "width": 520, "height": 260 },
    "inventory": { "x": 1410, "y": 350, "width": 460, "height": 600 }
  },
  "ui": {
    "open_interface": "none",
    "selected_tab": "inventory",
    "cursor_state": "interact",
    "hover_text": "Chop down Tree",
    "elements": [
      { "id": "inv_slot_1", "type": "slot", "label": "Logs", "state": "occupied" }
    ],
    "dialogue_options": []
  },
  "ocr": [
    { "bbox": [12, 834, 240, 860], "text": "You chop the tree." }
  ],
  "derived": {
    "location": { "region": "Lumbridge", "subarea": "South trees" },
    "activity": { "type": "woodcutting", "state": "active", "progress": 0.4 },
    "combat": { "state": "out_of_combat" }
  },
  "account": {
    "name": "gillimo",
    "membership_status": "f2p",
    "skills": { "woodcutting": 15, "fishing": 1 },
    "inventory": [ "Bronze axe", "Logs x12" ],
    "equipment": { "weapon": "Bronze axe" },
    "resources": { "gp": 1200 }
  },
  "constraints": {
    "risk_tolerance": "low",
    "time_budget_minutes": 30,
    "allowed_zones": [ "safe" ],
    "preferred_activities": [ "skilling", "questing" ]
  },
  "objectives": {
    "preset": "make_best_money_f2p",
    "short_term": [ "Fill inventory with logs", "Bank logs" ],
    "medium_term": [ "Reach woodcutting 20" ],
    "long_term": [ "Sustainable low-risk money route" ]
  }
}
```

Schema reference: `SNAPSHOT_SCHEMA.md`.

## Gaps to Close
- Reliable minimap parsing for location inference.
- OCR accuracy on small fonts and fast chat updates.
- Consistent UI element detection across client scaling settings.
- Mapping of UI elements to action affordances without ambiguity.
- F2P method catalog accuracy (gp/hour and requirements).
