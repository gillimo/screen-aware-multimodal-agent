# Canonical Loop (JSON Action Intents)

## Documentation Positioning
AgentOSRS is documented as a screen-aware, autonomous OSRS agent with a JSON-first execution loop. The documentation prioritizes:
- A local-first, auditable agent that perceives the screen, decides via models, and acts through humanized input.
- Structured data contracts for perception (`SNAPSHOT_SCHEMA.md`) and action intents (`MODEL_OUTPUT_SCHEMA.md`).
- Execution safety (policy gating, approval, and logging) as the default posture for live inputs.

Free-text command loops exist for testing and manual probing, but they are not the canonical automation path.

## Core Loop (Canonical)
1) Capture snapshot (must conform to `SNAPSHOT_SCHEMA.md`).
2) Build decision context and prompt from snapshot + goal.
3) Model emits JSON action intents (per `MODEL_OUTPUT_SCHEMA.md`).
4) Validate decision output and log the decision trace.
5) Convert intents into `ActionIntent` objects.
6) Enforce policy + approval gating before live execution.
7) Execute intents with humanization and per-action timing/motion.
8) Capture post-action snapshots and verify outcomes.
9) Log action results, action context, and execution summary.
10) Update state and repeat.

## Scope Notes
- The `go` CLI path is the reference orchestration for the canonical loop.
- Tutorial Island JSON loop is a focused instance of the same action-intent workflow.
