# Screen-Aware Local Multimodal Agent
## What It IsStart 2023-10-01 — Early CLI-piped coding assistant prototype. 100% complete; no open issues. Historical artifact that proves early tool-loop design.## How It Works- Start 2023-10-01 — Early CLI-piped coding assistant prototype. 100% complete; no open issues. Historical artifact that proves early tool-loop design.## What It IsStart 2023-10-01 — Original Oct 2023 local agent release. 100% complete; no open issues. Prompt-to-action loop with safe execution as the seed for later stacks.## How It Works- Start 2023-10-01 — Original Oct 2023 local agent release. 100% complete; no open issues. Prompt-to-action loop with safe execution as the seed for later stacks.## What It IsStart 2026-01-20 — Reusable scoring and rating engine. 100% complete; no open issues. Deterministic metrics, calibration flow, and audit-ready outputs.## How It Works- Start 2026-01-20 — Reusable scoring and rating engine. 100% complete; no open issues. Deterministic metrics, calibration flow, and audit-ready outputs.## What It IsStart 2025-12-17 — Full-stack scoring engine with heuristics, caches, CLI/GUI, and evaluation flow. Multi‑signal weighting, role balancing, and draft optimization with explainable outputs. Designed to stress-test ranking logic, iteration velocity, and production‑grade scoring pipelines.## How It Works- Start 2025-12-17 — Full-stack scoring engine with heuristics, caches, CLI/GUI, and evaluation flow. Multi‑signal weighting, role balancing, and draft optimization with explainable outputs. Designed to stress-test ranking logic, iteration velocity, and production‑grade scoring pipelines.## What It IsStart 2023-09-29 — Foundational local automation agent with prompt-to-action loops. 100% complete; no open issues. Compact architecture with command extraction, safety gates, and retry flow.## How It Works- Start 2023-09-29 — Foundational local automation agent with prompt-to-action loops. 100% complete; no open issues. Compact architecture with command extraction, safety gates, and retry flow.## What It IsStart 2026-01-12 — Reusable agent/data template. 100% complete; no open issues. Standardized CLI/GUI, config, docs, and validation scaffolding.## How It Works- Start 2026-01-12 — Reusable agent/data template. 100% complete; no open issues. Standardized CLI/GUI, config, docs, and validation scaffolding.## What It IsBuild a Rust-first, low-latency Polymarket arbitrage engine where latency is the first gate. The system hunts long-tail mispricings, executes two-leg trades with strict risk controls, and proves positive EV through auditable logs and iteration. No LLMs in the hot path.## How It Works- See README sections below for details on components and flow.## What It IsStart 2026-01-15 — Emulator-driven RL lab with OCR/vision, control loops, and reward shaping. Full environment interface, action abstraction, and telemetry for rapid iteration. Built to validate agent behaviors, stabilize training loops, and prove applied RL engineering under constraints.## How It Works- Start 2026-01-15 — Emulator-driven RL lab with OCR/vision, control loops, and reward shaping. Full environment interface, action abstraction, and telemetry for rapid iteration. Built to validate agent behaviors, stabilize training loops, and prove applied RL engineering under constraints.## What It IsStart 2026-01-06 — Local multimodal agent with perception → planning → humanized execution. OCR, UI state parsing, local model routing, and action intent loops with safety gates. Engineered to generalize across UI tasks while preserving human-like input patterns and pacing.## How It Works- Start 2026-01-06 — Local multimodal agent with perception → planning → humanized execution. OCR, UI state parsing, local model routing, and action intent loops with safety gates. Engineered to generalize across UI tasks while preserving human-like input patterns and pacing.

Mission Learning Statement
- Mission: Build a screen-aware local multimodal agent with perception, planning, and humanized input.
- Learning focus: multimodal perception, state modeling, and robust action execution loops.
- Project start date: 2026-01-06 (inferred from earliest git commit)

## Overview
This project demonstrates a local, autonomous agent that can perceive a screen, decide on actions,
and execute human-like input patterns. It is designed to generalize to multiple application domains
by separating perception, reasoning, and execution layers.

## Core Capabilities
- Screen capture with region targeting and frame pacing
- OCR and visual cue detection for UI state
- Local model integration for decision-making
- Humanized input execution (mouse/keyboard timing profiles)
- JSON-first action intent loop for deterministic runs

## Quick Start
```bash
python run_app.py status
python run_app.py plan
python run_app.py gui
```

## Architecture (High Level)
```
perceive() -> decide() -> act() -> validate() -> repeat
```

## Notes
Legacy internal docs may reference domain-specific integrations. The core techniques
and architecture are intentionally domain-agnostic.

## Metadata
- Completeness: 68%
- Known issues: Domain-specific docs remain; rsprox fork untracked

