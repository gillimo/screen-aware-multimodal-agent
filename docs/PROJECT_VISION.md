# Project Vision

## The Goal

Build an **autonomous, task-agnostic OSRS agent** that plays the game the way a human does - by observing the screen, understanding what's happening, reasoning about what to do, and acting with natural human-like input patterns.

## Core Philosophy

### 1. Autonomy Over Scripting

Traditional bots follow hardcoded scripts: "click here, wait 2 seconds, click there." AgentOSRS is different. It:

- **Observes** the game state through vision (screen capture, OCR, object detection)
- **Reasons** about what to do using local AI models
- **Acts** based on understanding, not memorized coordinates
- **Adapts** to unexpected situations (dialogue boxes, random events, obstacles)

The agent doesn't need to know the pixel coordinates of the "Talk to" option. It reads the hover text, sees "Talk to Survival Expert," and decides to click.

### 2. Task-Agnostic Design

The agent isn't built for one specific activity. The same perception and action systems work for:

- Questing (following dialogue, navigating, interacting with NPCs)
- Skilling (woodcutting, fishing, mining, crafting)
- Combat (targeting, eating food, managing prayer)
- Banking (depositing, withdrawing, organizing)
- Navigation (walking paths, using teleports, opening doors)

Give it a goal, and it figures out the steps by understanding what it sees.

### 3. Human Equivalence

The agent must be **statistically indistinguishable** from a human player:

**Input Patterns**
- Mouse moves with natural curves, not straight lines
- Click timing varies like human reaction times
- Occasional mistakes and corrections
- Micro-tremors and jitter in slow movements

**Session Behavior**
- Attention drifts and wanders
- Periodic idle behaviors (camera glances, inventory checks)
- Activity comes in bursts with rest periods
- Performance degrades slightly over long sessions (fatigue)

**Tick Awareness**
- OSRS runs on 600ms game ticks
- Actions are paced to align with tick boundaries
- No superhuman reaction times or perfect timing

### 4. Local-First Operation

Everything runs on your machine:

- **Local perception** - Screen capture and analysis happen locally
- **Local decisions** - Ollama runs AI models without cloud calls
- **Local storage** - All data, logs, and models stay on disk
- **Optional escalation** - Claude API available for complex vision tasks, but not required

No telemetry, no cloud dependencies, no external services required.

## Architecture Layers

### Eyes (Perception)

The agent sees the game through multiple channels:

| Channel | What It Provides |
|---------|------------------|
| Screen Capture | Raw pixels at configurable FPS |
| OCR Engine | Text from chat, hover, tooltips, UI labels |
| Object Detection | ML classification of items, NPCs, objects |
| RuneLite Plugin | Structured data (position, NPCs, inventory) |
| Color Detection | Highlights, interactables, health bars |
| UI Parsing | Panel states, open interfaces, tabs |

Output: A **snapshot** - a JSON document describing everything visible on screen.

### Brain (Decision)

The agent thinks using AI models:

| Model | Role |
|-------|------|
| Local LLM (Phi3) | Fast decisions from text state |
| Claude Vision | Complex scene understanding (escalation) |
| ML Classifier | Object/NPC/item recognition |

Input: Snapshot + goal + context
Output: **ActionIntent** - what to do next (click, move, type, wait)

Action intents are emitted as JSON and validated against `MODEL_OUTPUT_SCHEMA.md`.
This JSON action-intent loop is the canonical automation path (see `CORE_LOOP.md`).

### Hands (Execution)

The agent acts through humanized input:

| Action | Humanization |
|--------|--------------|
| Mouse Move | Bezier curves, jitter, speed variance |
| Click | Dwell time, down/up timing, occasional miss |
| Keyboard | Typing cadence, modifier timing |
| Camera | Organic rotation, slight over-rotation |

All actions pass through the **humanization layer** which adds natural variance.

### Validation Loop

After every action:
1. Capture new state
2. Verify expected change occurred
3. Retry with adjustment if needed
4. Log outcome for learning

## What Success Looks Like

### Near-Term
- Agent completes Tutorial Island autonomously
- Recognizes common NPCs, items, and objects via ML
- Maintains human-like input patterns across sessions
- Handles basic unexpected situations (dialogue, random events)

### Medium-Term
- Completes F2P quests by understanding objectives
- Trains skills efficiently with adaptive pacing
- Manages inventory and banking autonomously
- Navigates the game world using visual landmarks

### Long-Term
- Handles any task given natural language goals
- Learns from mistakes and improves over time
- Maintains statistical human-equivalence under analysis
- Operates for extended sessions with realistic behavior

## Technical Differentiators

| Traditional Bot | AgentOSRS |
|-----------------|-----------|
| Hardcoded coordinates | Vision-based targeting |
| Fixed scripts | AI-driven decisions |
| Perfect timing | Human-like variance |
| Single-purpose | Task-agnostic |
| Cloud-dependent | Local-first |
| Detectable patterns | Statistical human-equivalence |

## Guiding Constraints

1. **Never superhuman** - No actions faster or more precise than human capability
2. **Understand, don't memorize** - Decisions come from perception, not lookup tables
3. **Fail gracefully** - Unknown situations trigger pause and re-evaluation, not crashes
4. **Audit everything** - Every decision and action is logged for analysis
5. **Local by default** - External services are optional enhancements, not requirements

## The Name

**AgentOSRS** - An agent, not a bot. It perceives, reasons, and acts. It has eyes to see, hands to interact, and a brain to decide. It's autonomous but bounded, capable but constrained to human-equivalent behavior.
