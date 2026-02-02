# Screen-Aware Local Multimodal Agent

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

