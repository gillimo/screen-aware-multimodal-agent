# AgentOSRS Function Index

Quick reference for all available functions. **Check here before building new features.**

---

## SETUP REQUIREMENTS

### 1. RuneLite Plugin (REQUIRED for game data)
The agent needs the Session Stats plugin to get game state.

**Build:**
```bash
cd runelite_plugin
./gradlew.bat build
```

**Install:**
1. Copy `build/libs/session-stats-1.0.jar` to RuneLite plugins folder
2. OR load as external plugin in RuneLite Developer Tools

**Verify:**
- Check file exists: `~/.runelite/session_stats.json`
- Should update every 2 game ticks

### 2. Local Model (Ollama)
```bash
# Install Ollama, then:
ollama pull phi3:mini
```

Config: `data/local_model.json`

### 3. ML Classifier (Optional, improves vision)
```bash
pip install torch torchvision
python scripts/train_classifier.py
```

---

---

## INPUT EXECUTION (`src/input_exec.py`)

| Function | Output | Description |
|----------|--------|-------------|
| `move_mouse(x, y)` | None | Instant move to absolute coords |
| `move_mouse_path(x, y, steps=30, step_delay_ms=8)` | None | Smooth linear A-to-B movement |
| `click(button="left", dwell_ms=None)` | None | Mouse click with proper timing |
| `get_cursor_pos()` | `(x, y)` | Current cursor position |
| `type_text(text, delay_ms=None)` | None | Type unicode text |
| `press_key(vk_code, hold_ms=None)` | None | Press virtual key code |
| `press_key_name(name, hold_ms=None)` | None | Press by name (F1-F24, ESC, SPACE, etc.) |
| `scroll(amount)` | None | Mouse wheel scroll |
| `drag(start, end, hold_ms=None)` | None | Click-drag operation |

---

## CHAT/DIALOGUE LOGGING (`src/game_actions.py`)

| Function | Output | Description |
|----------|--------|-------------|
| `get_chat_logger()` | `ChatLogger` | Get global chat logger instance |
| `log_chat(text, source, **kwargs)` | None | Log chat entry |
| `get_recent_chat(n=10)` | `List[Dict]` | Get recent chat entries |
| `ChatLogger.log_dialogue(info, phase)` | None | Log from DialogueInfo |
| `ChatLogger.load_history(limit=100)` | `List[Dict]` | Load chat history from file |

---

## TUTORIAL HINT INGESTION (`src/game_actions.py`)

| Function | Output | Description |
|----------|--------|-------------|
| `get_tutorial_hint(snapshot)` | `str` | Extract tutorial hint text |
| `get_all_screen_text(snapshot)` | `Dict[str, str]` | All OCR text by region |
| `log_tutorial_hint(snapshot, phase)` | None | Log hint to chat log |

---

## DIALOGUE HANDLING (`src/game_actions.py`)

### Keyboard-Based (PREFERRED)
| Function | Output | Description |
|----------|--------|-------------|
| `press_dialogue_continue()` | `ActionResult` | Press SPACE to continue |
| `press_dialogue_option(option_number)` | `ActionResult` | Press 1-5 to select option |
| `handle_dialogue_keyboard(snapshot, option_preference=None)` | `ActionResult` | Auto-handle dialogue with keyboard |

### Mouse-Based (Legacy)
| Function | Output | Description |
|----------|--------|-------------|
| `click_dialogue_continue(snapshot, window_bounds)` | `ActionResult` | Click to continue |
| `click_dialogue_option(option_index, snapshot, window_bounds)` | `ActionResult` | Click option |
| `select_dialogue_by_text(target_text, snapshot, window_bounds)` | `ActionResult` | Find and click matching option |

### Detection
| Function | Output | Description |
|----------|--------|-------------|
| `detect_dialogue_state(snapshot)` | `DialogueInfo` | Detect dialogue type and content |

---

## PERCEPTION (`src/fast_perception.py`)

| Function | Output | Description |
|----------|--------|-------------|
| `perceive(window_bounds=None, use_rust=True, use_runelite=True)` | `PerceptionResult` | Full perception with NPCs, position, arrows |
| `capture_snapshot(window_bounds=None)` | `Dict` | Full snapshot with OCR |
| `find_npc(name)` | `(x, y)` or None | Find NPC screen position |
| `get_tutorial_phase()` | `str` | Current tutorial phase |
| `is_player_idle()` | `bool` | Check if player is idle |
| `rust_available()` | `bool` | Check if Rust module loaded |

---

## RUNELITE DATA (`src/runelite_data.py`)

| Function | Output | Description |
|----------|--------|-------------|
| `read_export()` | `Dict` or None | Read RuneLite JSON export |
| `is_data_fresh(max_age_seconds=2.0)` | `bool` | Check if data is recent |
| `find_npc_on_screen(name)` | `(x, y)` or None | Find NPC by name |
| `get_player_position()` | `(x, y, plane)` or None | World coordinates |
| `get_tutorial_phase()` | `str` | Tutorial progress phase |
| `is_player_idle()` | `bool` | Player idle check |
| `get_inventory_items()` | `List[Dict]` | Current inventory |

---

## OCR (`src/ocr.py`)

| Function | Output | Description |
|----------|--------|-------------|
| `run_ocr(regions, provider_name="tesseract", provider_config=None)` | `List[OcrEntry]` | Run OCR on regions |
| `register_provider(name, provider)` | None | Register custom OCR provider |
| `get_provider(name)` | `OcrProvider` | Get registered provider |

**OcrEntry**: `region: str`, `text: str`, `confidence: float`

---

## GAME ACTIONS (`src/game_actions.py`)

### Hover & Interaction
| Function | Output | Description |
|----------|--------|-------------|
| `get_hover_text(snapshot)` | `str` | Extract hover text from OCR |
| `find_object_by_hover(hover_text, snapshot, window_bounds, snapshot_fn)` | `(x, y)` or None | Search for object by hovering |
| `interact_with_object(target_text, snapshot, window_bounds, snapshot_fn, action="left")` | `ActionResult` | Find and click object |

### NPC Interaction
| Function | Output | Description |
|----------|--------|-------------|
| `find_npc_position(npc_name, snapshot)` | `(x, y)` or None | Get NPC screen coords |
| `interact_with_npc(npc_name, snapshot, window_bounds, snapshot_fn, action="Talk-to")` | `ActionResult` | Click on NPC |

### Inventory
| Function | Output | Description |
|----------|--------|-------------|
| `click_inventory_slot(slot_index, window_bounds)` | `ActionResult` | Click inventory slot |
| `use_item_on_target(item_slot, target_x, target_y, window_bounds)` | `ActionResult` | Use item on target |

### Walking
| Function | Output | Description |
|----------|--------|-------------|
| `click_minimap(dx, dy, window_bounds)` | `ActionResult` | Click minimap for walking |
| `rotate_camera(direction, duration_ms)` | `ActionResult` | Rotate camera |

---

## ARROW DETECTION (`src/arrow_detector.py`)

| Function | Output | Description |
|----------|--------|-------------|
| `find_yellow_arrow(image)` | `(x, y)` or None | Find yellow tutorial arrow |
| `find_arrow_target(image)` | `Dict` | `{found, x, y, confidence}` |

---

## AUTONOMY (`src/autonomy.py`)

### Inventory
| Function | Output | Description |
|----------|--------|-------------|
| `parse_inventory_from_runelite(runelite_data)` | `InventoryState` | Parse inventory |
| `find_item_in_inventory(inventory, item_name)` | `int` or None | Find item slot |
| `find_empty_slot(inventory)` | `int` or None | Find empty slot |
| `count_item(inventory, item_name)` | `int` | Count item quantity |
| `is_inventory_full(snapshot)` | `bool` | Check if inventory full |
| `use_item_on_object(item_name, object_name, ...)` | `ActionResult` | Use item on object |

### Banking
| Function | Output | Description |
|----------|--------|-------------|
| `detect_bank_open(snapshot)` | `bool` | Check if bank is open |
| `open_bank(snapshot, window_bounds, ...)` | `ActionResult` | Open bank |
| `deposit_all(window_bounds)` | `ActionResult` | Deposit all items |
| `deposit_item(item_name, ...)` | `ActionResult` | Deposit specific item |
| `withdraw_item(item_name, ...)` | `ActionResult` | Withdraw item |
| `close_bank(window_bounds)` | `ActionResult` | Close bank |

### Combat & Status
| Function | Output | Description |
|----------|--------|-------------|
| `detect_in_combat(snapshot)` | `bool` | Check if in combat |
| `get_health_percent(snapshot)` | `float` | Current HP percentage |
| `detect_death(snapshot)` | `bool` | Check if player died |
| `is_player_idle(snapshot, idle_ticks=3)` | `bool` | Idle status |

### Random Events
| Function | Output | Description |
|----------|--------|-------------|
| `detect_random_event(snapshot)` | `str` or None | Detect random event |
| `handle_random_event(snapshot, window_bounds, ...)` | `ActionResult` | Handle random event |

### World State
| Function | Output | Description |
|----------|--------|-------------|
| `parse_world_state(snapshot)` | `WorldState` | Parse world info |

---

## LOCAL MODEL (`src/local_model.py`)

| Function | Output | Description |
|----------|--------|-------------|
| `run_local_model(prompt, config=None)` | `str` | Query local LLM |

---

## CHAT FILTER (`src/chat_filter.py`)

| Function | Output | Description |
|----------|--------|-------------|
| `is_random_event_message(lines)` | `bool` | Check for random event text |
| `should_respond_to_chat(lines)` | `bool` | Should we respond to chat |

---

## SCREEN CAPTURE (`src/perception.py`)

| Function | Output | Description |
|----------|--------|-------------|
| `capture_frame(bounds)` | `Dict` | Capture screen region |
| `find_window(title_contains)` | `Dict` | Find window by title |

---

## TIMING & HUMANIZATION

### Pacing (`src/pacing.py`)
| Function | Output | Description |
|----------|--------|-------------|
| `sample_pacing_delay(profile, action_type)` | `float` | Human-like delay |
| `sample_burst_pause(profile)` | `float` | Pause after burst |

### Timing (`src/timing.py`)
| Function | Output | Description |
|----------|--------|-------------|
| `sample_inter_action_delay(profile)` | `float` | Delay between actions |
| `apply_fatigue_modifier(delay, fatigue_level)` | `float` | Fatigue-adjusted delay |

---

## ACTIONS FRAMEWORK (`src/actions.py`)

| Function | Output | Description |
|----------|--------|-------------|
| `validate_action_intent(intent)` | `List[str]` | Validate intent |
| `execute_with_retry(executor, intent, profile)` | `ActionResult` | Execute with retries |
| `pre_action_gate(intent, snapshot)` | `List[str]` | Pre-action checks |
| `post_action_verify(result, snapshot)` | `bool` | Verify action succeeded |

---

## AGENT COMMANDS (`src/agent_commands.py`)

| Function | Output | Description |
|----------|--------|-------------|
| `parse_model_command(text)` | `(cmd, args)` | Parse command from model output |
| `get_available_commands()` | `List[str]` | List all commands |
| `get_context_for_model(snapshot)` | `Dict` | Build context for model |

**AgentCommandExecutor class methods:**
- `execute(command, args)` -> `CommandResult`
- `_continue_dialogue()` -> `CommandResult`
- `_select_option(option_text)` -> `CommandResult`
- `_click_npc(npc_name)` -> `CommandResult`
- `_click_object(object_name)` -> `CommandResult`
- `_use_item(item_name)` -> `CommandResult`
- `_walk_direction(direction)` -> `CommandResult`

---

## DATA FILES

| File | Purpose |
|------|---------|
| `data/ocr_regions.json` | OCR region coordinates |
| `data/ocr_config.json` | OCR provider settings |
| `data/profiles.json` | Behavior profiles |
| `data/agent_state.json` | Agent state |
| `data/agent_decisions.json` | Decision rules |

---

## KEY DATA STRUCTURES

### ActionResult
```python
@dataclass
class ActionResult:
    intent_id: str
    success: bool
    failure_reason: Optional[str] = None
    details: Optional[Dict] = None
```

### DialogueInfo
```python
@dataclass
class DialogueInfo:
    state: DialogueState  # NONE, NPC_CHAT, PLAYER_OPTIONS, SYSTEM_MESSAGE
    npc_name: str
    text: str
    options: List[str]
    continue_available: bool
```

### PerceptionResult
```python
@dataclass
class PerceptionResult:
    runelite_fresh: bool
    player_position: Optional[Tuple[int, int]]
    player_world: Optional[Tuple[int, int, int]]
    camera_direction: str
    npcs_on_screen: list
    tutorial_progress: int
    inventory_count: int
    arrow_position: Optional[Tuple[int, int]]
    arrow_confidence: float
    highlight_position: Optional[Tuple[int, int]]
```

---

*Last updated: 2026-01-07*
