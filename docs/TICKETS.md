# Ticket Log

## Canonical JSON Action-Intent Loop (HIGH PRIORITY)

Align automation to the JSON action-intent pipeline and its contracts.

- [x] Make the JSON action-intent loop the default automation path; keep free-text commands test-only. (canonical_loop.py)
- [x] Ensure snapshot capture outputs `SNAPSHOT_SCHEMA.md` fields (client, roi, cues, derived, account, stale, runelite_data) or add an adapter layer. (snapshot_schema.py)
- [x] Wire decision validation + trace logging into the canonical loop before execution. (canonical_loop.py)
- [x] Execute intents through policy/approval gating and log action context + execution summaries in the same loop. (canonical_loop.py)
- [x] Align tutorial loop orchestration with the canonical action-intent pipeline (state updates, cues, and decision replay). (canonical_loop.py, tutorial_phases.py)
- [ ] Retire or fix legacy loop timing issues (e.g., double sleep) once canonical loop owns timing.
- [x] Define RSProx-first pipeline stages with explicit timing budgets and short-circuit rules. (canonical_loop.py, rust_core/integration.rs)
- [x] Gate heavy OCR/snapshot capture behind stuck/uncertain triggers; keep RSProx hot path lightweight. (snapshot_schema.py)
- [x] Define fallback triggers (stuck, low-confidence, verification failures) and recovery flow. (snapshot_schema.py)
- [x] Establish minimal normalization contract for model/executor input; add optional enrichment path. (rust_core/integration.rs)
- [x] Define logging boundaries for hot path vs fallback (always-on vs on-demand logs). (canonical_loop.py)

## Game Logic Layer (PRIORITY - Current Sprint)

The foundation (eyes, hands, humanization) is solid. These tickets fill the gap between perception/action and autonomous gameplay.

### Dialogue Handling (src/game_actions.py)
- [x] Detect dialogue box open state from UI snapshot
- [x] Parse dialogue options from OCR (numbered choices)
- [x] Implement click-dialogue-option by option index or text match
- [x] Handle "Click here to continue" prompts
- [x] Handle NPC chat vs player dialogue vs system messages
- [x] Add dialogue state tracking (in_dialogue, dialogue_npc, last_option)

### Walking & Navigation (src/game_actions.py)
- [x] Implement walk-to-tile by clicking minimap
- [x] Implement walk-to-object by clicking game view (via find_object_by_hover)
- [x] Add pathfinding fallback (click intermediate points) - walk_waypoints(), walk_direction()
- [x] Detect when player is stuck (position not changing)
- [x] Add camera rotation to find off-screen targets
- [x] Implement "search and walk" pattern (rotate camera, scan, walk)

### NPC Interaction Flow (src/game_actions.py)
- [x] Implement full NPC interaction: find → hover → verify text → click
- [x] Handle right-click menu for action selection (Talk-to, Trade, Attack)
- [x] Add NPC tracking when target moves during approach - TrackedNPC, track_npc()
- [x] Implement "follow NPC" for moving targets - follow_npc()
- [x] Add interaction validation (did dialogue open? did action start?) - validate_interaction()

### Inventory Management (src/game_actions.py)
- [x] Implement click-inventory-slot by slot number (0-27)
- [x] Implement find-item-in-inventory by item name/hover text - find_item_slot_by_hover()
- [x] Implement use-item-on-item (click item, click target)
- [x] Implement use-item-on-object (click item, click game object) - in _use() command
- [x] Implement drop-item with shift-click
- [x] Add inventory state tracking (what's in each slot) - scan_inventory_slots()

### Object Interaction (src/game_actions.py)
- [x] Implement click-object by hover text match
- [x] Handle objects requiring specific actions (chop, mine, fish) - via interact_with_object()
- [x] Add object state detection (tree chopped, rock depleted) - detect_object_state()
- [x] Implement wait-for-object-respawn pattern - wait_for_object_respawn()

### Error Recovery (src/game_actions.py)
- [ ] Replace silent `pass` blocks with proper error handling
- [x] Add recovery strategies for common failures:
  - [x] Target not found → rotate camera → retry
  - [x] Click missed → re-aim → retry - click_with_verify() with spiral search
  - [x] Dialogue unexpected → close → retry (via ESCAPE)
  - [x] Inventory full → handle gracefully - handle_inventory_full(), InventoryFullStrategy
- [x] Add stuck detection (no progress for N ticks)
- [x] Implement reset-to-known-state fallback - reset_to_known_state()

### State Machine Framework (src/state_machine.py)
- [x] Create generic Phase class with entry/exit/tick methods
- [x] Implement phase transition detection from game state
- [x] Add phase-specific action selection logic
- [x] Create phase registry for different activities (questing, skilling)
- [x] Implement goal-driven phase sequencing
- [x] Add common phase implementations (WaitPhase, DialoguePhase, InteractPhase, WalkPhase)
- [x] Create Tutorial Island example phases

## Autonomy Features (PRIORITY - Next Sprint)

Core autonomous behaviors that make the agent self-sufficient.

### Pathfinding & Navigation
- [x] Multi-waypoint pathfinding (click intermediate points) - walk_waypoints(), Waypoint class
- [x] Obstacle detection and avoidance - autonomy_features.py ObstacleDetector
- [x] Door/gate auto-open when blocked - detect_blocking_door(), try_open_door(), walk_with_door_handling()
- [x] Stuck detection with auto-unstick - StuckState class, auto_unstick()
- [x] Long-distance navigation using landmarks - autonomy_features.py LandmarkNavigator, LANDMARKS
- [x] Region-based navigation hints - autonomy_features.py, snapshot_schema.py _infer_region()

### Inventory Intelligence (src/autonomy.py)
- [x] Track inventory state (item in each slot 0-27)
- [x] Find item by name/ID in inventory
- [x] Detect inventory full condition
- [x] Smart item organization (stack similar items) - autonomy_features.py ItemOrganizer
- [x] Use-item-on-object flow (click item, click world object)
- [x] Equipment management (equip/unequip items) - equip_item(), unequip_item(), EQUIPMENT_SLOTS

### Skilling Loops (src/autonomy.py)
- [x] Generic skilling loop framework (find resource → interact → wait → repeat)
- [x] Woodcutting loop (find tree → chop → wait for logs → repeat)
- [x] Fishing loop (find spot → fish → wait → repeat)
- [x] Mining loop (find rock → mine → wait for ore → repeat)
- [x] Resource depletion detection (tree gone, rock empty)
- [x] Auto-drop for power training
- [x] Inventory full → bank trip logic

### Banking (src/autonomy.py)
- [x] Detect bank interface open
- [x] Click bank booth/banker to open
- [x] Deposit all items
- [x] Deposit specific items - deposit_item(item_name, quantity)
- [x] Withdraw items by name/quantity - withdraw_item(item_name, quantity)
- [x] Close bank interface
- [x] Bank trip loop (walk to bank → deposit → walk back)

### Combat (src/autonomy.py)
- [x] Detect combat state (in combat vs idle)
- [x] Target selection (click enemy)
- [x] Auto-attack continuation
- [x] Health monitoring (eat food when low)
- [x] Prayer flicking (if applicable) - autonomy_features.py PrayerFlicker
- [x] Loot pickup after kill
- [x] Safe-spot detection and usage - autonomy_features.py SafeSpotDetector
- [x] Run away when health critical

### Random Events (src/autonomy.py)
- [x] Detect random event spawn (NPC following player)
- [x] Common random event handlers:
  - [x] Dismiss unwanted events
  - [x] Genie lamp (click for XP)
  - [x] Quiz master (answer questions) - autonomy_features.py QuizMasterHandler
  - [x] Frog princess (kiss frog) - autonomy_features.py FrogPrincessHandler
- [x] Pause main activity during random event
- [x] Resume after random event resolved

### World Awareness (src/autonomy.py)
- [x] Player position tracking (via RuneLite data)
- [x] Nearby NPC detection
- [x] Nearby player detection (for safety)
- [x] Resource availability scanning - autonomy_features.py ResourceScanner
- [x] Death detection and respawn handling
- [x] Login/logout state handling - LoginState enum, detect_login_state(), handle_disconnect()

### Activity Scheduler (src/autonomy.py)
- [x] Time-based activity switching
- [x] XP/hour tracking per skill - SkillXP, XPTracker classes with xp_per_hour(), format_summary()
- [x] Goal-based activity selection (e.g., "get 40 fishing") - autonomy_features.py GoalBasedPlanner
- [x] Break scheduling (human-like session patterns)
- [x] Daily task rotation - autonomy_features.py DailyRotation

### Agent Command Interface (src/agent_commands.py)
- [x] Simple text command parser (talk_to, click, chop, etc.)
- [x] AgentCommander class for executing commands
- [x] Context builder for model decision making
- [x] Automatic random event handling
- [x] Available commands list for model prompts

### Autonomous Agent Loop (src/autonomous_agent.py)
- [x] Complete perceive → decide → act loop
- [x] Local model integration with prompt templates
- [x] Priority action handling (random events, health, dialogue)
- [x] Failure tracking and recovery
- [x] Session summary and statistics
- [x] CLI interface with goal specification

## Performance Optimization - Rust Core (Future)
Note: Target is processing within 1 game tick (~600ms)
- [ ] Evaluate Rust for performance-critical components
- [ ] Rust module for screen capture and ROI extraction
- [ ] Rust module for fast pixel analysis (arrow detection, highlights)
- [ ] PyO3 bindings for Python integration
- [ ] Keep Python for decision making, Rust for perception
- [ ] Benchmark: capture->detect->decide->act in <600ms
- [ ] Consider: Rust WebSocket client for RuneLite instead of file polling

## RuneLite API Integration (Priority) - BLOCKED

**STATUS: BLOCKED** - Custom RuneLite plugins cannot load with Jagex Launcher auth.
Standard RuneLite only loads plugins from the official Plugin Hub.
Dev-mode RuneLite doesn't work with Jagex account authentication.

**Original approach (blocked):**
- [ ] ~~Extend RuneLite plugin to expose game data via local socket/file~~

**New approach: RSProx Integration (see below)**

---

## RSProx Game Data API (PRIORITY - Unblocks Everything)

**Problem**: Need game state data (player position, NPCs, inventory, skills, varps) but:
- Custom RuneLite plugins don't work with Jagex Launcher authentication
- Only Plugin Hub plugins load in standard RuneLite

**Solution**: Use [RSProx](https://github.com/blurite/rsprox) - a packet proxy that:
- ✅ Works with Jagex Account authentication (fully supported)
- ✅ Works with RuneLite as the client
- ✅ Intercepts ALL game packets at network level
- ✅ Already decodes player info, NPCs, inventory, skills, varps
- ✅ Open source (MIT license)

**Implementation Plan**:

### Phase 1: Fork RSProx and Add HTTP API
- [ ] Fork RSProx to `rsprox_fork/` (DONE - cloned to agentosrs/rsprox_fork)
- [ ] Study existing architecture:
  - `transcriber/state/SessionState.kt` - holds player, NPCs, varps, XP
  - `transcriber/state/SessionTracker.kt` - updates state from packets
  - `transcriber/state/World.kt` - holds NPCs map
  - `proxy/http/HttpServerHandler.kt` - existing HTTP server (port 8081)
- [ ] Add new HTTP endpoints to HttpServerHandler:

**Endpoints to implement:**
```
GET /gamestate    - Full game state snapshot (JSON)
GET /player       - Local player: index, name, coord (level, x, z)
GET /npcs         - Nearby NPCs: index, id, name, coord, angle
GET /inventory    - Inventory contents (requires tracking UpdateInv packets)
GET /skills       - All skill levels and XP
GET /varps        - Varp values (for tutorial progress varbit 281, etc.)
GET /camera       - Camera position (from CAM_* packets)
```

**JSON response format (matches our existing RuneLite plugin schema):**
```json
{
  "timestamp": 1704654321000,
  "tick": 12345,
  "player": {
    "index": 2047,
    "name": "PlayerName",
    "coord": {"level": 0, "x": 3100, "z": 3200}
  },
  "npcs": [
    {"index": 1, "id": 3308, "name": "Survival Expert", "coord": {...}}
  ],
  "skills": {"attack": {"level": 1, "xp": 0}, ...},
  "varps": {"281": 10}
}
```

### Phase 2: Connect RSProx State to HTTP
- [ ] Expose SessionState from transcriber module to proxy module
- [ ] Add singleton/registry for active session state
- [ ] Wire HTTP handler to read from SessionState
- [ ] Add JSON serialization for Player, Npc, World data
- [ ] Handle multiple sessions (if multiple clients connected)

### Phase 3: Python Client
- [ ] Create `src/rsprox_client.py` to fetch from RSProx HTTP API
- [ ] Replace file-based RuneLite data reader with HTTP client
- [ ] Update `fast_perception.py` to use RSProx data
- [ ] Test with live game session

### Phase 4: Integration
- [ ] Update agent to use RSProx data for:
  - Player position tracking
  - NPC detection and targeting
  - Skill level checks
  - Tutorial progress (varbit 281)
- [ ] Remove dependency on custom RuneLite plugin
- [ ] Document RSProx setup in README

**Key Files in RSProx:**
- `transcriber/state/SessionState.kt` - Main state container
  - `localPlayerIndex: Int` - Which player is us
  - `getPlayer(index): Player` - Get player coord
  - `getActiveWorld(): World` - Get world with NPCs
  - `getVarp(id): Int` - Get varp values
  - `getExperience(skill): Int` - Get skill XP
- `transcriber/state/Player.kt` - `data class Player(index, name, coord)`
- `transcriber/state/Npc.kt` - `data class Npc(index, id, name, coord, angle)`
- `transcriber/state/World.kt` - Has `npcs: MutableMap<Int, Npc>`
- `proxy/http/HttpServerHandler.kt` - Add our endpoints here

**Build & Run RSProx:**
```bash
cd rsprox_fork
./gradlew proxy   # Launches RSProx GUI
# Select Jagex Account mode, link account, launch RuneLite
# HTTP server runs on port 8081
```

**Estimated Effort**: Medium (Kotlin changes, but architecture is clean)

---

## RuneLite Plugin Hub Submission (Backup Plan)
If RSProx approach has issues, try submitting to Plugin Hub:
- [ ] Simplify plugin to minimal data export (JSON file only)
- [ ] Frame as "Session Stats Logger" for personal use
- [ ] Submit PR to runelite/plugin-hub
- [ ] Risk: May be rejected for automation potential

---

## Periodic Cloud Model Strategic Planning (Future)

**Concept**: Every hour, call Claude (cloud model) for high-level strategic planning while local model handles tick-by-tick decisions.

**Architecture**:
- Local model (Phi3/Ollama): Fast, tick-rate decisions - "click this NPC", "walk here"
- Cloud model (Claude): Hourly strategic planning - "next hour: train fishing to 40, then start Cook's Assistant quest"

**Implementation**:
- [ ] Create `src/strategic_planner.py` module
- [ ] Schedule hourly cloud model call (configurable interval)
- [ ] Pass current game state summary to Claude:
  - All skill levels and XP
  - Inventory contents
  - Current location
  - Quest status
  - Bank contents (if recently banked)
  - Recent activity log
- [ ] Claude returns strategic plan:
  - Next hour's goals (prioritized list)
  - Suggested activities
  - Risk assessment (PKers, random events)
  - Break recommendations
- [ ] Store plan in `data/strategic_plan.json`
- [ ] Local model references plan for context
- [ ] Track plan execution progress
- [ ] Re-plan early if major events (death, quest complete, goal reached)

**Benefits**:
- Local model stays fast (no API latency for decisions)
- Cloud model provides intelligent long-term strategy
- Reduces API costs (1 call/hour vs continuous)
- Better goal-oriented behavior

## Tutorial Island Autonomous Completion (Priority)
Note: Quest Helper does NOT cover Tutorial Island - must handle ourselves
- [x] Define Tutorial Island phases and transitions
- [x] Create tutorial_island_decisions.json with phase-based actions
- [ ] Implement Gielinor Guide phase (character creation done)
- [ ] Implement Survival Expert phase (fishing, cooking, fire)
- [ ] Implement Master Chef phase (bread making)
- [ ] Implement Quest Guide phase (quest tab intro)
- [ ] Implement Mining Instructor phase (mining, smithing)
- [ ] Implement Combat Instructor phase (melee, ranged)
- [ ] Implement Financial Advisor phase (bank intro)
- [ ] Implement Brother Brace phase (prayer, friends tab)
- [ ] Implement Magic Instructor phase (spellcasting, leaving island)
- [ ] Add phase detection from tutorial hint OCR
- [ ] Add phase transition verification
- [ ] Test end-to-end Tutorial Island completion

## Hands and Eyes (Focused)
- [x] Build client window discovery and focus tracking. (perception_infra.py WindowTracker)
- [x] Implement screen capture with FPS and ROI configuration. (perception_infra.py ScreenCapture)
- [x] Track capture latency and dropped-frame metrics per session. (perception_infra.py MetricsTracker)
- [x] Add OCR backend with pluggable providers and per-region confidence scoring. (perception_infra.py OCRManager)
- [x] Add OCR config file and provider hook (noop/tesseract) with basic calibration helper.
- [x] Create UI element detector for core panels and tabs. (perception_infra.py UIDetector)
- [x] Implement minimap parsing for region inference. (perception_infra.py MinimapParser)
- [x] Add cursor state and hover text extraction. (perception_infra.py CursorTracker)
- [x] Define and validate the snapshot schema (JSON). (snapshot_schema.py)
- [x] Build a "capture and annotate" dataset tool. (agent_tools.py DatasetCapture)
- [x] Add a replay viewer for frame sequences and UI overlays. (agent_tools.py ReplayViewer)
- [x] Define a unified action API (move, click, drag, key, scroll). (agent_tools.py UnifiedAction)
- [x] Define the expected model output schema for action intents and constraints.
- [x] Add mouse pathing with curve/easing presets.
- [x] Add timing variance (dwell, jitter, reaction delay). (agent_tools.py TimingVariance)
- [x] Implement drag actions with human-like start and end jitter. (agent_tools.py HumanDrag)
- [x] Add focus recovery before any input execution.
- [x] Add action gating with UI pre-checks and abort rules.
- [x] Implement dry-run mode with action logging only.
- [x] Add post-action verification with bounded retry and failure classification - ActionVerification, execute_with_verification()
- [x] Add human-in-the-loop approval toggle for unsafe actions. (agent_tools.py ApprovalManager)
- [x] Add hardware device enumeration for mouse/keyboard with metadata capture. (agent_tools.py DeviceEnumerator)
- [x] Add device-level input profiles (DPI, polling rate, accel) for timing modeling. (agent_tools.py ProfileManager)
- [x] Detect display refresh rate and OS input latency (where supported). (agent_tools.py DisplayInfo)
- [ ] Define pass/fail acceptance criteria for perception parity.
- [ ] Define pass/fail acceptance criteria for timing/motion parity.
- [ ] Define pass/fail acceptance criteria for error and recovery parity.
- [ ] Build a human session capture + annotation pipeline.
- [ ] Build a replay-to-comparison harness (agent vs. human).
- [ ] Add calibration tooling to fit distributions to human baselines.
- [ ] Add a reporting pipeline for parity results and regressions.

- [ ] Add project-specific datasets in data/reference.json.
- [ ] Expand dependency graph for key workflows.
- [x] Implement model integration in src/local_model.py.
- [ ] Define end-to-end architecture for a screen-aware agent (modules, data flow, storage, failure modes).
- [ ] Build screen capture pipeline with configurable FPS and region-of-interest support.
- [ ] Add an OCR layer with a pluggable backend (local model or external provider).
- [ ] Add a UI element detector pipeline for buttons, minimap, chat, and inventory slots.
- [ ] Implement state extraction into a normalized UI snapshot schema with timestamps.
- [ ] Create a short-term planner (single-session goals, next action selection).
- [ ] Create a medium-term planner (quest, leveling, or skilling milestones).
- [ ] Create a long-term planner (account progression roadmap, week/month targets).
- [ ] Implement a plan store (JSONL) with revision history and rationale fields.
- [ ] Add a skill/ability model that maps account stats, gear, and unlocks to action viability.
- [ ] Implement action executor interfaces (mouse move/click, keyboard input, camera control).
- [ ] Add variable click timing (jitter and configurable distributions) for input actions.
- [x] Add non-linear mouse pathing (curves and easing) for mouse move actions.
- [x] Add a reaction-time model (stimulus-to-action delay) with per-action distributions.
- [x] Add hover dwell before click to simulate target acquisition.
- [x] Add occasional mouse overshoot with corrective micro-moves.
- [x] Add click down/up dwell variance and long-press support for drag actions.
- [x] Add misclick/near-miss modeling with corrective behavior (configurable rate).
- [x] Add scroll wheel speed variance and pause patterns for scroll actions.
- [ ] Add mouse acceleration profiles (DPI, OS speed, accel curve) with presets.
- [ ] Add inter-action micro-pauses based on task complexity and recent activity.
- [ ] Add handoff latency between mouse and keyboard actions.
- [x] Add session rhythm modeling (breaks, fatigue, time-based drift).
- [ ] Add repetition breakers to vary timing/pathing across repeated actions.
- [x] Add camera nudge variability instead of always perfect positioning.
- [x] Add focus checks (re-hover or re-read UI state) before committing actions.
- [ ] Add local-model chat responses when a player name is detected (opt-in, rate-limited, context-aware).
- [ ] Add per-user behavior profiles (timing, movement, mistakes) to avoid a single signature.
- [x] Add stochastic idle behaviors (hover, camera glance, inventory check) within safe bounds.
- [x] Add UI scan patterns before actions (mouse sweep or hover checks).
- [ ] Add “hesitation” mechanics before high-impact actions (bank, trade, drop).
- [x] Add corrective camera adjustments after minor overshoot or misclick.
- [ ] Add target acquisition model (aim point selection within UI bounds).
- [ ] Add click pressure simulation (down/up cadence by action type).
- [x] Add typing cadence modeling (key delays, bursts, corrections, backspace).
- [ ] Add chat cooldown rules (per player, per session, per channel).
- [ ] Add input device noise model (USB polling jitter, frame-time variance).
- [x] Add action chaining variability (different orderings for equivalent steps).
- [x] Add “attention drift” model that slightly biases cursor paths over time.
- [x] Add safe interrupt handling (pause on unexpected UI, resume with re-check).
- [ ] Add reaction to interruptions (randomized delay or abort on new modal).
- [x] Add human-like camera movement (short nudges, occasional over-rotation).
- [x] Add UI focus recovery (click back into client if focus lost).
- [ ] Add gesture variability for drag actions (speed, curvature, end jitter).
- [ ] Add context-based pacing (slow down in complex scenes, speed up in simple ones).
- [x] Add per-action confidence gating (extra checks when uncertainty is high).
- [ ] Add cursor settle behavior (brief stillness before final click).
- [x] Add edge avoidance for mouse paths (avoid perfectly straight to corners).
- [x] Add double-click variance for UI actions that use multi-click patterns.
- [ ] Add drag start hesitation and end jitter (human-like drag endpoints).
- [x] Add click targeting bias toward text center or icon center with drift.
- [x] Add long idle recovery behavior (re-orient UI, re-check state).
- [x] Add screen edge pauses (cursor leaves client briefly, returns).
- [x] Add off-screen cursor travel patterns for modal dismissal or refocus.
- [x] Add viewport scanning before interacting with new UI panels.
- [x] Add user-like camera zoom variation with pauses.
- [x] Add retry strategy for failed interactions (back off, re-aim, re-try).
- [ ] Add stochastic delay after action completion (human confirmation pause).
- [ ] Add keypress overlap modeling (shift+click timing variance).
- [ ] Add modifier key usage variance (shift, ctrl) where applicable.
- [x] Add action abort behavior when UI changes mid-action.
- [x] Add input burst modeling (short spurts followed by rest).
- [x] Add action spacing based on in-game animations or cooldown cues.
- [x] Add cursor speed ramps (accelerate/decay rather than constant velocity).
- [ ] Add micro-tremor noise in slow cursor movements (sub-pixel jitter).
- [x] Add target re-aim when hitbox shifts (moving entities).
- [x] Add element occlusion handling (wait or reposition when obstructed).
- [x] Add context-specific click cadence presets (banking vs. skilling).
- [x] Add probabilistic check of hover text before click.
- [x] Add “human slips” in camera drag (slight vertical drift).
- [x] Add randomized start point for mouse moves (from last idle position).
- [ ] Add edge-of-screen bounce avoidance for cursor travel.
- [x] Add short “thinking” pauses after UI state changes.
- [x] Add “double-check” loop for irreversible actions (drop, alch, trade).
- [x] Add alternate pathing for camera rotation (different drag directions).
- [x] Add periodic UI tab toggles (inventory, skills, quests) when idle.
- [x] Add panic pause on unexpected chat or trade window.
- [ ] Add shift-queue timing variance for repeated actions.
- [x] Add per-session seed control for reproducible randomness in testing.
- [x] Add configurable humanization presets (subtle, normal, heavy).
- [x] Add action context logger for timing/motion features to enable tuning.
- [x] Add decision_id to action context logs for run correlation.
- [x] Define end-state human mimicry benchmarks (timing, motion, error rates, session rhythm).
- [ ] Build a human-likeness scoring harness using recorded sessions as reference.
- [ ] Add replay-to-comparison tooling (compare agent traces vs. human traces).
- [x] Add acceptance criteria for “human-like” in docs (thresholds and examples).
- [ ] Add calibration tooling to fit timing/motion distributions to human baselines.
- [ ] Add evaluation datasets for input traces (mouse, click, camera) from real sessions.
- [ ] Add per-module KPI tracking for human-likeness (input, camera, response).
- [x] Apply HUMAN_MIMICRY_RUBRIC per run and persist scores (e.g., logs/mimicry_scores.jsonl).
- [ ] Define stimulus parity requirements (visual cues vs. structured JSON inputs).
- [ ] Add perception parity checks to ensure agent reacts to on-screen cues.
- [ ] Add visual cue extraction for animations, hover text, highlights, and overlays.
- [ ] Add structured-state augmentation pipeline (merge JSON state with visual cues).
- [ ] Add evaluation comparing structured-only vs. visual-augmented behavior.
- [ ] Add human-like pacing model tied to animation and UI feedback cues.
- [x] Add a sandbox action mode for dry runs that logs actions without executing them.
- [x] Define `SCHEMAS.md` as the source of truth for all schema docs.
- [ ] Add and maintain `STATE_SCHEMA.md` for `data/state.json`.
- [ ] Add and maintain `SNAPSHOT_SCHEMA.md` for screen-aware snapshots.
- [x] Add schema validation checks for `data/state.json` in the CLI.
- [x] Add schema validation for snapshot payloads in perception pipeline.
- [x] Create an end-state acceptance checklist tying END_STATE goals to ticket completion.
- [x] Add configuration storage for humanization presets and per-user profiles.
- [x] Define calibration workflow for human-like baselines (data capture, fitting, review).
- [x] Define data retention/privacy policy for action traces and screenshots.
- [x] Define model output/decision schema for planner and action intents.
- [x] Create Mimicry and Model acceptance checklist tied to END_STATE goals.
- [x] Create a Mimicry and Model overview doc that consolidates scope, schemas, tickets, and dependencies.
- [ ] Implement a feedback loop: action result → updated state → plan adjustment.
- [ ] Build a task scheduler to prioritize near-term actions while respecting long-term goals.
- [ ] Add a policy layer for allowed action types, rate limits, and cooldowns.
- [ ] Add a human-in-the-loop mode with step-by-step approval toggles.
- [ ] Build a silent, click-through overlay for the OSRS original client (no RuneLite dependency).
- [ ] Ensure overlay can attach to the OSRS client window and track resize/move.
- [ ] Add a “capture & annotate” tool for labeling screens to improve UI detection.
- [x] Add structured logging for every decision and action with timestamps.
- [x] Add decision trace viewer UI (minimal CLI/TUI) for log inspection.
- [x] Add scheduled compression/rotation for decision logs.
- [x] Add strict JSON retry policy config (max attempts) for model outputs.
- [x] Enforce active humanization profile in live executor (non-dry-run).
- [x] Ingest human-likeness KPI output into metrics reporting.
- [ ] Build replay tooling to review sessions from logs and screenshots.
- [ ] Implement performance profiling for capture, OCR, and planning loops.
- [ ] Add unit tests for planner logic and state parsing.
- [ ] Add integration tests with recorded screen sessions.
- [ ] Extend docs for vision, scope, and operational workflow of the agent.
- [ ] Add a compliance review section in docs covering acceptable use, user consent, and risk boundaries.
- [x] Add a monitoring/audit log spec that records inputs, decisions, and actions for post-run review.
- [ ] Add a safety checklist for any deployment or live testing (manual review steps, rollback plan).
- [x] Add an emergency stop key (Esc) to abort execution loops for regaining control.
- [ ] Design a GUI control panel with presets (e.g., “Make best money”, “Train for best money”, “Quest unlock path”).
- [ ] Implement GUI presets mapping to planner goals and constraints.
- [ ] Add a custom goal builder UI (select skills, target levels, time budget, risk tolerance).
- [ ] Add a session summary panel showing chosen preset, planned steps, and expected outcomes.
- [ ] Add accessibility options for the agent UI (font size scaling, high-contrast theme, reduced motion).
- [ ] Add configurable UI hotkeys for common actions (start, pause, next step, open logs).
- [ ] Add screen reader labels and focus order for all GUI controls.
- [ ] Add F2P-only defaults and constraints in planner presets (no members methods by default).
- [ ] Build a state snapshot schema for screen-aware inputs (window, ROI, UI, OCR, derived state).
- [ ] Implement a location inference layer using minimap parsing and landmark detection.
- [ ] Add UI element classification for core tabs and interfaces (inventory, bank, quests, skills).
- [ ] Implement activity inference (idle/moving/skilling/combat) from UI and OCR signals.
- [ ] Add a knowledge base for F2P methods with requirements and expected gp/xp.
- [ ] Align END_STATE and docs with OSRS original client overlay as primary (no RuneLite dependency).
- [ ] Implement `data/state.json` schema validation with required sections from END_STATE.
- [ ] Add state migration tooling to upgrade older `data/state.json` files safely.
- [ ] Add a state editor UI for account mode, members flag, goals, and unlocks.
- [ ] Populate F2P quest list and quest dependency graph (F2P-only scope).
- [ ] Implement planning scoring (value, time, risk) with weighted alternatives.
- [ ] Add result tracking to update plan outcomes and adjust future recommendations.
- [ ] Build overlay UI content for top 3 plan steps, ratings, and blockers.
- [ ] Build Tk UI tabs for plan, quests, ratings, notes, and chat.
