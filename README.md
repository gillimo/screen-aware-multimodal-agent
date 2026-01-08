# AgentOSRS

An autonomous, task-agnostic OSRS agent with **eyes**, **hands**, and **human-like behavior**.

## Vision

AgentOSRS is designed to be an **autonomous agent** that can play Old School RuneScape like a human would - by seeing the screen, understanding what's happening, making decisions, and executing actions with natural, human-like input patterns.

### Core Principles

**Autonomous** - The agent makes its own decisions. Given a goal, it observes the game state, reasons about what to do next, and acts without constant guidance.

**Task-Agnostic** - Not hardcoded for specific quests or activities. The agent can adapt to any situation by understanding what it sees on screen - hover text, UI elements, chat messages, and game objects.

**Eyes (Perception)**
- Screen capture with configurable FPS and regions of interest
- OCR for reading chat, hover text, tooltips, and UI labels
- Object/NPC/item recognition via ML classifiers trained on OSRS Wiki images
- RuneLite plugin integration for structured game data (player position, NPCs, inventory)
- Visual cue detection (highlights, interactables, dialogue options)

**Hands (Input Execution)**
- Mouse movement with human-like curves, jitter, and micro-tremors
- Click timing with natural dwell, reaction delays, and variance
- Keyboard input with realistic typing cadence and chorded keys
- Camera control with organic rotation patterns

**Human Mimicry**
- Tick-aligned timing (600ms game ticks, actions paced accordingly)
- Attention drift and gaze patterns
- Idle behaviors (camera glances, inventory checks, brief pauses)
- Session rhythm (activity bursts, rest periods, fatigue simulation)
- Error modeling (occasional misclicks, corrections, recovery)
- Statistical equivalence to human input traces

**Local-First**
- Runs entirely on your machine - no cloud dependencies
- Local LLM integration (Ollama/Phi3) for decision-making
- Claude API available for complex vision tasks when needed
- All data stays local in `data/` and `logs/`

## Architecture

Canonical automation uses the JSON action-intent loop (snapshot -> model output -> intent execution). Free-text command loops are test-only.

```
┌─────────────────────────────────────────────────────────────┐
│                         AGENT LOOP                          │
│   perceive() → decide() → act() → validate() → repeat       │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│      EYES       │  │      BRAIN      │  │      HANDS      │
│                 │  │                 │  │                 │
│ Screen Capture  │  │ Local Model     │  │ Mouse Movement  │
│ OCR Engine      │  │ (Ollama/Phi3)   │  │ Click Execution │
│ Object Detect   │  │                 │  │ Keyboard Input  │
│ RuneLite Data   │  │ Claude Vision   │  │ Camera Control  │
│ UI Parsing      │  │ (escalation)    │  │ Humanization    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    HUMANIZATION LAYER                       │
│  Timing variance, curves, jitter, attention drift, pacing   │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Run the autonomous agent (ensure RuneLite is open)
python -m src.autonomous_agent --goal "complete tutorial island"

# With options
python -m src.autonomous_agent --goal "train fishing" --max-ticks 500

# Or use the legacy wrapper
python -m src.agent_runner --max 50 --sleep 2.0

# CLI commands
python run_app.py status    # Check current state
python run_app.py plan      # View/edit plan
python run_app.py gui       # Open GUI
```

## Key Components

| Component | Description |
|-----------|-------------|
| `src/autonomous_agent.py` | Main autonomous agent loop with goal-driven behavior |
| `src/agent_commands.py` | Simple command interface for the local model |
| `src/autonomy.py` | Autonomous behaviors (skilling, banking, combat) |
| `src/game_actions.py` | High-level game interactions (dialogue, NPC, inventory) |
| `src/state_machine.py` | Phase-based state machine with goal sequencing |
| `src/fast_perception.py` | Unified perception (Rust + RuneLite + Python) |
| `src/local_model.py` | Local LLM integration via Ollama |
| `src/input_exec.py` | Low-level mouse/keyboard via Windows API |
| `src/humanization.py` | Human-like motion and timing profiles |
| `rust_core/` | Native screen capture and pixel detection |
| `runelite_plugin/` | RuneLite plugin for game data export |
| `scripts/` | Dataset building and model training |

## ML Dataset

The agent builds a visual recognition dataset from the OSRS Wiki:

```
data/ml_dataset/
├── items/
│   ├── weapons/melee/dragon/
│   ├── armor/helmets/
│   └── food/fish/
├── npcs/
│   ├── monsters/slayer/
│   └── services/bankers/
├── objects/
│   └── scenery/trees/oak/
└── ...
```

Train the classifier:
```bash
python scripts/download_all_wiki.py  # Download ALL wiki images
python scripts/train_classifier.py    # Train ResNet18 model
```

## Configuration

| File | Purpose |
|------|---------|
| `data/agent_state.json` | Current agent state (phase, progress) |
| `data/agent_decisions.json` | Decision templates by phase |
| `data/humanization_profiles.json` | 6 behavior profiles (timing, motion) |
| `data/local_model.json` | Ollama configuration |
| `data/roi.json` | Screen regions of interest |

## Documentation

See `docs/` for detailed specifications:
- `PROJECT_VISION.md` - Full project vision and goals
- `HANDS_AND_EYES.md` - Perception and action requirements
- `HUMAN_EQUIVALENCE.md` - Human-like behavior validation criteria
- `HUMANIZATION_PROFILES.md` - Behavior profile definitions
- `SNAPSHOT_SCHEMA.md` - Game state snapshot format

## Requirements

- Python 3.10+
- RuneLite client
- Ollama with Phi3 model (for local decisions)
- PyTorch (for ML training)
- Windows (for native input execution)

## Status

The project is ~70% complete with:
- Perception system fully operational
- Local decision-making loop functional
- Action execution with humanization implemented
- ML dataset pipeline in progress

See `docs/HANDS_AND_EYES.md` for the complete feature checklist.
