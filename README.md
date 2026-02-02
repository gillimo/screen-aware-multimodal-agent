# Screen-Aware Multimodal Agent (AgentOSRS)

Mission Learning Statement
- Mission: Build a screen-aware local multimodal agent with perception, planning, and humanized input.
- Learning focus: multimodal perception, state modeling, and robust action execution loops.
- Project start date: 2026-01-06 (inferred from earliest git commit)

Autonomous agent that perceives the screen, decides on actions, and executes human-like input patterns.

## Features

- Screen capture + OCR for UI state
- Object/NPC/item recognition and RuneLite data hooks
- Local model decision loop with optional cloud escalation
- Humanized input execution (timing, curves, jitter)

## Installation

### Requirements

- Python 3.10+
- RuneLite (for plugin data)
- Local model runtime (Ollama)

## Quick Start

```bash
python -m src.autonomous_agent --goal "complete tutorial island"
python -m src.autonomous_agent --goal "train fishing" --max-ticks 500
python -m src.agent_runner --max 50 --sleep 2.0
```

## Usage

- `python run_app.py status` to check current state
- `python run_app.py plan` to view/edit plans
- `python run_app.py gui` to open the GUI

## Architecture

```
Perception (Eyes)
  |-- Screen Capture
  |-- OCR + UI Parsing
  |-- RuneLite Data
        |
        v
Decision (Brain)
  |-- Local Model
  |-- Policies + State Machine
        |
        v
Execution (Hands)
  |-- Mouse + Keyboard
  |-- Humanization Layer
```

## Project Structure

```
src/                # Core agent loop and behaviors
rust_core/          # Native capture and pixel detection
runelite_plugin/    # RuneLite data export
scripts/            # Dataset and training tools
data/               # Local datasets and logs
```

## Building

No build step required. Run directly with Python.

## Contributing

See `docs/` for architecture and internal notes.

## License

No license file is included in this repository.
