# Automation Concepts (Architecture Only)

This document is conceptual. It focuses on architecture and safety, not step-by-step automation instructions.

## Concepts
- Action scoring engine: rank candidate activities by expected value.
- Decision loop: choose next task based on rewards, time, and risk.
- Outcome logging: record results to refine future recommendations.
- Constraints: apply ironman/pure rules to filter options.
- Action execution: human-like input timing, motion, and pacing profiles.
- Stimulus parity: react to the same cues a human can see on-screen.

## Manual Alternatives
- Use CLI or GUI to pick tasks.
- Execute tasks manually in-game.
- Record results in `data/session_log.json`.

## Safety
- Action execution is opt-in and constrained by policy settings.
- Maintain auditable logs for all input and decision steps.
