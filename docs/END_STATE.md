# End State (AgentOSRS)

This describes the target outcome for the AgentOSRS project.

## Product Scope
- OSRS decision agent with two front-ends:
  - OSRS original client silent overlay (primary).
  - Tkinter companion UI for deep planning and notes.
- Automation is a core goal, driven by structured JSON state plus screen perception.

## Data Model (Authoritative)
- `data/state.json` is the source of truth and is versioned.
- Required state sections:
  - account: name, mode (main, iron, hc, pure), members, combat level, gp, playstyle.
  - skills: all OSRS skills (levels only).
  - quests: completed, in_progress, not_started.
  - diaries: by region with tiers completed.
  - gear: loadouts by style + utility items.
  - unlocks: spellbooks, teleports, minigames, QoL.
  - goals: short, mid, long.

## Planning Engine
- Choose next tasks based on value, time, and risk.
- Track outcomes and learn from results.
- Provide alternatives (fast, cheap, safe).

## UI
- Overlay: top 3 plan steps, ratings, blockers.
- Tk UI: tabs for plan, quests, ratings, notes, chat.

## Safety
- Action execution is opt-in and gated by policy controls.
- Human-like input behavior is the long-term target for interaction realism.
