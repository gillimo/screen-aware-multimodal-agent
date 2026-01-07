# State JSON Schema (data/state.json)

Purpose: define the required structure for `data/state.json`.

## Required Top-Level Fields
- version: number
- account: object
- skills: object
- quests: object
- diaries: object
- gear: object
- unlocks: object
- goals: object

## account
- name: string
- mode: string (main, iron, hc, pure)
- combat_level: number
- gp: number
- playstyle: string
- members: boolean

## skills
- All OSRS skills with numeric levels.

## quests
- completed: array of strings
- in_progress: array of strings
- not_started: array of strings

## diaries
- region keys with tier values (none, easy, medium, hard, elite).

## gear
- melee: array of strings
- ranged: array of strings
- magic: array of strings
- utility: array of strings

## unlocks
- spellbooks: array of strings
- teleports: array of strings
- minigames: array of strings

## goals
- short: array of strings
- mid: array of strings
- long: array of strings

## Example
```json
{
  "version": 1,
  "account": {
    "name": "gillimo",
    "mode": "main",
    "combat_level": 80,
    "gp": 1500000,
    "playstyle": "balanced",
    "members": true
  },
  "skills": { "attack": 70, "strength": 70 },
  "quests": { "completed": [], "in_progress": [], "not_started": [] },
  "diaries": { "lumbridge": "easy" },
  "gear": { "melee": [], "ranged": [], "magic": [], "utility": [] },
  "unlocks": { "spellbooks": [], "teleports": [], "minigames": [] },
  "goals": { "short": [], "mid": [], "long": [] }
}
```
