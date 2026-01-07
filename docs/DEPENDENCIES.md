# Quest Dependencies (Approach)

This file defines how the coach should map and surface quest dependencies.

## Dependency Types
- Skill level requirements
- Quest prerequisites
- Item requirements
- Location access requirements
- Combat or boss requirements

## Output Style
- Show the shortest path to unlock a target quest.
- Show alternate paths when multiple prerequisites exist.
- Include required items and where to obtain them.

## Priority Quest Chains (examples)
- Barrows gloves chain: Recipe for Disaster subquests and prereqs.
- Fairy rings: Fairy Tale II (partial completion).
- Spirit trees: Tree Gnome Village + The Grand Tree.
- Fossil Island access: Bone Voyage.
- Barrows access: Priest in Peril.
- Dragon weapons: Lost City (for dragon dagger), Monkey Madness (dragon scim).
- Piety: Kings Ransom + Knights training grounds + prerequisites.
- Ancients: Desert Treasure.
- Lunars: Lunar Diplomacy.
- Arceuus spellbook: Client of Kourend.
- Ava device: Animal Magnetism.
- Slayer helm: Slayer points and unlocks.

## Data Plan
- Store quest data in `data/quests.json` with fields:
  - name, skill_reqs, quest_reqs, item_reqs, unlocks, notes
- Build a dependency graph at runtime and cache it.
