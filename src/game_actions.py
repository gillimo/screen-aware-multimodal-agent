"""
Game Logic Layer - High-level game interactions built on the action system.

This module provides:
- Dialogue handling (detecting, reading, selecting options)
- NPC interaction (find, hover, verify, click, handle menu)
- Object interaction (find by hover text, click with action)
- Inventory management (click slots, use items, drop)
- Walking/Navigation (minimap clicks, camera rotation)
"""
from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable

from src.actions import ActionIntent, ActionResult, LiveExecutor, ActionLogger
from src.input_exec import move_mouse_path, click, get_cursor_pos, press_key_name

from pathlib import Path
import json
from datetime import datetime


# =============================================================================
# CHAT/DIALOGUE LOGGING
# =============================================================================

class ChatLogger:
    """
    Logs all chat and dialogue for tracking progress.

    User note: "some chat doesnt imply progress until we hit a checkpoint"
    So we log everything and let the decision system determine progress.
    """

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or Path(__file__).resolve().parents[1] / "data" / "chat_log.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: List[Dict[str, Any]] = []

    def log(self,
            text: str,
            source: str = "unknown",
            npc_name: str = "",
            options: Optional[List[str]] = None,
            phase: str = "") -> None:
        """
        Log a chat/dialogue entry.

        Args:
            text: The dialogue text
            source: "npc", "player", "system", "tutorial"
            npc_name: Name of NPC if applicable
            options: Dialogue options if player choice
            phase: Current tutorial/game phase
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "text": text,
            "npc_name": npc_name,
            "options": options or [],
            "phase": phase,
        }
        self._entries.append(entry)

        # Append to file
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def log_dialogue(self, info: "DialogueInfo", phase: str = "") -> None:
        """Log from DialogueInfo object."""
        if info.state == DialogueState.NONE:
            return

        source = "npc" if info.state == DialogueState.NPC_CHAT else "player_choice"
        if info.state == DialogueState.SYSTEM_MESSAGE:
            source = "system"

        self.log(
            text=info.text,
            source=source,
            npc_name=info.npc_name,
            options=info.options,
            phase=phase,
        )

    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get the n most recent entries."""
        return self._entries[-n:]

    def load_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Load chat history from file."""
        if not self.log_path.exists():
            return []

        entries = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        return entries[-limit:]


# Global chat logger instance
_chat_logger: Optional[ChatLogger] = None


def get_chat_logger() -> ChatLogger:
    """Get or create the global chat logger."""
    global _chat_logger
    if _chat_logger is None:
        _chat_logger = ChatLogger()
    return _chat_logger


def log_chat(text: str, source: str = "unknown", **kwargs) -> None:
    """Convenience function to log chat."""
    get_chat_logger().log(text, source, **kwargs)


def get_recent_chat(n: int = 10) -> List[Dict[str, Any]]:
    """Get recent chat entries."""
    return get_chat_logger().get_recent(n)


# =============================================================================
# TUTORIAL HINT INGESTION
# =============================================================================

def get_tutorial_hint(snapshot: Dict[str, Any]) -> str:
    """
    Extract tutorial hint text from snapshot.

    Tutorial hints appear in the tutorial_hint OCR region and guide
    the player through Tutorial Island.
    """
    ocr_data = snapshot.get("ocr", [])
    for entry in ocr_data:
        if entry.get("region") == "tutorial_hint":
            return entry.get("text", "").strip()
    return ""


def get_all_screen_text(snapshot: Dict[str, Any]) -> Dict[str, str]:
    """
    Get all OCR text from all regions.

    Returns dict with region names as keys and text as values.
    """
    result = {}
    ocr_data = snapshot.get("ocr", [])
    for entry in ocr_data:
        region = entry.get("region", "unknown")
        text = entry.get("text", "").strip()
        if text:
            result[region] = text
    return result


def log_tutorial_hint(snapshot: Dict[str, Any], phase: str = "") -> None:
    """Log tutorial hint to chat log for tracking."""
    hint = get_tutorial_hint(snapshot)
    if hint:
        log_chat(hint, source="tutorial", phase=phase)


# =============================================================================
# UI TAB FUNCTIONS (Fixed Classic Layout)
# =============================================================================

# Tab positions relative to game window (Fixed Classic Layout)
# These are approximate pixel offsets from the window's top-left
UI_TABS = {
    "combat": {"x": 526, "y": 168},
    "skills": {"x": 559, "y": 168},
    "quest": {"x": 592, "y": 168},
    "inventory": {"x": 625, "y": 168},
    "equipment": {"x": 658, "y": 168},
    "prayer": {"x": 691, "y": 168},
    "magic": {"x": 724, "y": 168},
}

def open_inventory() -> ActionResult:
    """
    Open the inventory tab by pressing F1.
    This is the fastest and most reliable method.
    """
    press_key_name("F1", hold_ms=50)
    time.sleep(0.15)
    return ActionResult(
        intent_id="open_inventory",
        success=True,
        details={"method": "F1"}
    )


def open_prayer() -> ActionResult:
    """Open the prayer tab by pressing F5."""
    press_key_name("F5", hold_ms=50)
    time.sleep(0.15)
    return ActionResult(
        intent_id="open_prayer",
        success=True,
        details={"method": "F5"}
    )


def open_magic() -> ActionResult:
    """Open the magic tab by pressing F6."""
    press_key_name("F6", hold_ms=50)
    time.sleep(0.15)
    return ActionResult(
        intent_id="open_magic",
        success=True,
        details={"method": "F6"}
    )


def open_equipment() -> ActionResult:
    """Open the equipment tab by pressing F4."""
    press_key_name("F4", hold_ms=50)
    time.sleep(0.15)
    return ActionResult(
        intent_id="open_equipment",
        success=True,
        details={"method": "F4"}
    )


def open_combat() -> ActionResult:
    """Open the combat options tab by pressing F2."""
    press_key_name("F2", hold_ms=50)
    time.sleep(0.15)
    return ActionResult(
        intent_id="open_combat",
        success=True,
        details={"method": "F2"}
    )


def open_skills() -> ActionResult:
    """Open the skills tab by pressing F3."""
    press_key_name("F3", hold_ms=50)
    time.sleep(0.15)
    return ActionResult(
        intent_id="open_skills",
        success=True,
        details={"method": "F3"}
    )


def click_tab(tab_name: str, window_offset: Tuple[int, int] = (0, 0)) -> ActionResult:
    """
    Click a UI tab by name. Use keyboard shortcuts when possible.

    Args:
        tab_name: One of "combat", "skills", "quest", "inventory", "equipment", "prayer", "magic"
        window_offset: (x, y) offset of game window on screen
    """
    tab_name = tab_name.lower()

    # Use keyboard shortcuts for common tabs
    if tab_name == "inventory":
        return open_inventory()
    elif tab_name == "prayer":
        return open_prayer()
    elif tab_name == "magic":
        return open_magic()
    elif tab_name == "equipment":
        return open_equipment()
    elif tab_name == "combat":
        return open_combat()
    elif tab_name == "skills":
        return open_skills()

    # Fallback to clicking for quest tab (no F-key shortcut)
    if tab_name in UI_TABS:
        tab = UI_TABS[tab_name]
        x = window_offset[0] + tab["x"]
        y = window_offset[1] + tab["y"]
        move_mouse_path(x, y, steps=15)
        time.sleep(0.1)
        click()
        return ActionResult(
            intent_id=f"open_{tab_name}",
            success=True,
            details={"method": "click", "pos": (x, y)}
        )

    return ActionResult(
        intent_id="open_tab",
        success=False,
        failure_reason="unknown_tab",
        details={"tab_name": tab_name}
    )


# =============================================================================
# DIALOGUE HANDLING
# =============================================================================

class DialogueState(Enum):
    """Current dialogue state"""
    NONE = "none"
    NPC_CHAT = "npc_chat"           # NPC is talking, "Click to continue"
    PLAYER_OPTIONS = "player_options"  # Player has numbered options
    SYSTEM_MESSAGE = "system_message"  # System notification


@dataclass
class DialogueInfo:
    """Information about current dialogue"""
    state: DialogueState = DialogueState.NONE
    npc_name: str = ""
    text: str = ""
    options: List[str] = field(default_factory=list)
    continue_available: bool = False


def detect_dialogue_state(snapshot: Dict[str, Any]) -> DialogueInfo:
    """
    Detect if a dialogue box is open and parse its contents.

    Checks:
    - ui.open_interface for dialogue indicators
    - ui.dialogue_options for numbered choices
    - ocr regions for dialogue text
    """
    info = DialogueInfo()

    if not snapshot:
        return info

    ui = snapshot.get("ui", {})
    ocr = snapshot.get("ocr", [])

    # Check for dialogue options
    dialogue_options = ui.get("dialogue_options", [])
    if dialogue_options and len(dialogue_options) > 0:
        # Filter out noise - look for actual dialogue lines
        clean_options = []
        for opt in dialogue_options:
            if isinstance(opt, str) and len(opt) > 2:
                # Skip obvious noise (paths, system text)
                if not opt.startswith(("C:", "/", "\\", "http")):
                    clean_options.append(opt)

        if clean_options:
            info.options = clean_options
            info.state = DialogueState.PLAYER_OPTIONS

    # Check OCR for dialogue region
    for ocr_item in ocr:
        if not isinstance(ocr_item, dict):
            continue
        region = ocr_item.get("region", "")
        text = ocr_item.get("text", "")

        if region == "dialogue" and text:
            info.text = text
            # Check for "Click to continue" or similar
            if "click" in text.lower() and "continue" in text.lower():
                info.continue_available = True
                if info.state == DialogueState.NONE:
                    info.state = DialogueState.NPC_CHAT

        if region == "chat_box" and text:
            # Look for NPC name patterns (usually "Name:" format)
            name_match = re.search(r'^([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s*:', text)
            if name_match:
                info.npc_name = name_match.group(1)

    # Check open_interface for dialogue indicators
    open_interface = ui.get("open_interface", "none")
    if open_interface in ("dialogue", "npc_dialogue", "chat"):
        if info.state == DialogueState.NONE:
            info.state = DialogueState.NPC_CHAT

    return info


def click_dialogue_continue(
    snapshot: Dict[str, Any],
    window_bounds: Tuple[int, int, int, int],
) -> ActionResult:
    """
    Click to continue through NPC dialogue.
    Clicks in the chat area to advance.
    """
    win_x, win_y, win_w, win_h = window_bounds

    # Chat area is typically bottom-left, click center of it
    roi = snapshot.get("roi", {}).get("fixed", {}).get("chat_box", {})
    if roi:
        click_x = win_x + roi.get("x", 50) + roi.get("width", 400) // 2
        click_y = win_y + roi.get("y", 500) + roi.get("height", 150) // 2
    else:
        # Fallback to approximate chat area
        click_x = win_x + 250
        click_y = win_y + 550

    # Add some randomness
    click_x += random.randint(-30, 30)
    click_y += random.randint(-10, 10)

    move_mouse_path(click_x, click_y, steps=12, curve_strength=0.15)
    time.sleep(random.uniform(0.05, 0.12))
    click(button='left', dwell_ms=random.randint(40, 80))

    return ActionResult(
        intent_id="dialogue_continue",
        success=True,
        details={"click_pos": (click_x, click_y)}
    )


def click_dialogue_option(
    option_index: int,
    snapshot: Dict[str, Any],
    window_bounds: Tuple[int, int, int, int],
) -> ActionResult:
    """
    Click a numbered dialogue option (1-5 typically).

    In OSRS, dialogue options appear as a vertical list.
    Option 1 is at the top, each subsequent option is ~20px lower.
    """
    win_x, win_y, win_w, win_h = window_bounds

    # Dialogue options typically appear in center of screen
    # Base Y position for first option, then offset by index
    base_x = win_x + win_w // 2
    base_y = win_y + 280  # Approximate start of dialogue options
    option_height = 22  # Pixels between options

    click_x = base_x + random.randint(-40, 40)
    click_y = base_y + (option_index * option_height) + random.randint(-4, 4)

    move_mouse_path(click_x, click_y, steps=10, curve_strength=0.12)
    time.sleep(random.uniform(0.04, 0.10))
    click(button='left', dwell_ms=random.randint(35, 70))

    return ActionResult(
        intent_id=f"dialogue_option_{option_index}",
        success=True,
        details={"option_index": option_index, "click_pos": (click_x, click_y)}
    )


def select_dialogue_by_text(
    target_text: str,
    snapshot: Dict[str, Any],
    window_bounds: Tuple[int, int, int, int],
) -> ActionResult:
    """
    Select a dialogue option that contains the target text.
    """
    info = detect_dialogue_state(snapshot)

    if info.state != DialogueState.PLAYER_OPTIONS:
        return ActionResult(
            intent_id="dialogue_select",
            success=False,
            failure_reason="no_dialogue_options"
        )

    # Find matching option
    target_lower = target_text.lower()
    for idx, option in enumerate(info.options):
        if target_lower in option.lower():
            return click_dialogue_option(idx, snapshot, window_bounds)

    return ActionResult(
        intent_id="dialogue_select",
        success=False,
        failure_reason="option_not_found",
        details={"target": target_text, "available": info.options}
    )


# -----------------------------------------------------------------------------
# KEYBOARD-BASED DIALOGUE (faster and more reliable than mouse clicks)
# -----------------------------------------------------------------------------

def press_dialogue_continue() -> ActionResult:
    """
    Press spacebar to continue through NPC dialogue.
    Much faster and more reliable than clicking.
    """
    press_key_name("SPACE", hold_ms=50)
    time.sleep(0.15)  # Small delay for game to process

    return ActionResult(
        intent_id="dialogue_continue_key",
        success=True,
        details={"key": "SPACE"}
    )


def press_dialogue_option(option_number: int) -> ActionResult:
    """
    Press a number key (1-5) to select a dialogue option.
    Much faster and more reliable than clicking.

    Args:
        option_number: 1-5 for the dialogue option
    """
    if not 1 <= option_number <= 5:
        return ActionResult(
            intent_id="dialogue_option_key",
            success=False,
            failure_reason="invalid_option",
            details={"option": option_number, "valid_range": "1-5"}
        )

    press_key_name(str(option_number), hold_ms=50)
    time.sleep(0.15)  # Small delay for game to process

    return ActionResult(
        intent_id="dialogue_option_key",
        success=True,
        details={"key": str(option_number), "option": option_number}
    )


def handle_dialogue_keyboard(
    snapshot: Dict[str, Any],
    option_preference: Optional[int] = None,
) -> ActionResult:
    """
    Handle dialogue using keyboard only.

    - If NPC is talking: press spacebar to continue
    - If player has options: press the specified number, or 1 by default

    Args:
        snapshot: Game state snapshot
        option_preference: Which option to select (1-5), defaults to 1
    """
    info = detect_dialogue_state(snapshot)

    if info.state == DialogueState.NONE:
        return ActionResult(
            intent_id="dialogue_handle",
            success=False,
            failure_reason="no_dialogue"
        )

    if info.state == DialogueState.NPC_CHAT or info.continue_available:
        return press_dialogue_continue()

    if info.state == DialogueState.PLAYER_OPTIONS:
        option = option_preference if option_preference else 1
        # Make sure option is valid for available options
        if info.options and option > len(info.options):
            option = 1
        return press_dialogue_option(option)

    # System message - try spacebar
    return press_dialogue_continue()


# =============================================================================
# HOVER TEXT DETECTION
# =============================================================================

def get_hover_text(snapshot: Dict[str, Any]) -> str:
    """Extract current hover text from snapshot."""
    ui = snapshot.get("ui", {})
    hover = ui.get("hover_text", "")

    # Also check OCR hover region
    for ocr_item in snapshot.get("ocr", []):
        if isinstance(ocr_item, dict) and ocr_item.get("region") == "hover_text":
            ocr_hover = ocr_item.get("text", "")
            if ocr_hover and len(ocr_hover) > len(hover):
                hover = ocr_hover

    return hover


def hover_text_contains(snapshot: Dict[str, Any], target: str) -> bool:
    """Check if hover text contains target string (case-insensitive)."""
    hover = get_hover_text(snapshot)
    return target.lower() in hover.lower()


def parse_hover_actions(hover_text: str) -> List[str]:
    """
    Parse available actions from hover text.
    OSRS hover format: "Action1 / Action2 / Action3 Target"
    """
    if not hover_text:
        return []

    # Split by "/" which separates actions
    parts = hover_text.split("/")
    actions = []
    for part in parts:
        action = part.strip()
        if action:
            actions.append(action)

    return actions


# =============================================================================
# NPC INTERACTION
# =============================================================================

@dataclass
class NPCTarget:
    """Information about a target NPC"""
    name: str
    screen_x: int
    screen_y: int
    actions: List[str] = field(default_factory=list)
    confidence: float = 0.0


def find_npc_by_hover(
    target_name: str,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
    max_attempts: int = 20,
) -> Optional[NPCTarget]:
    """
    Find an NPC by scanning the game area and checking hover text.

    Scans a grid pattern, checking hover text at each position.
    Returns NPCTarget if found, None otherwise.
    """
    win_x, win_y, win_w, win_h = window_bounds

    # Define scan grid (game area, excluding UI panels)
    scan_start_x = win_x + 50
    scan_end_x = win_x + win_w - 250  # Avoid right panel
    scan_start_y = win_y + 50
    scan_end_y = win_y + win_h - 200  # Avoid bottom panel

    # Grid step size
    step_x = (scan_end_x - scan_start_x) // 5
    step_y = (scan_end_y - scan_start_y) // 4

    target_lower = target_name.lower()

    for attempt in range(max_attempts):
        # Randomize scan order for natural movement
        grid_points = []
        for gx in range(5):
            for gy in range(4):
                x = scan_start_x + gx * step_x + random.randint(-20, 20)
                y = scan_start_y + gy * step_y + random.randint(-15, 15)
                grid_points.append((x, y))

        random.shuffle(grid_points)

        for x, y in grid_points[:6]:  # Check 6 points per attempt
            move_mouse_path(x, y, steps=18, curve_strength=0.1, step_delay_ms=10)
            time.sleep(0.12)  # Pause to let hover text update

            snapshot = snapshot_fn()
            hover = get_hover_text(snapshot)

            if target_lower in hover.lower():
                actions = parse_hover_actions(hover)
                return NPCTarget(
                    name=target_name,
                    screen_x=x,
                    screen_y=y,
                    actions=actions,
                    confidence=0.9
                )

    return None


def interact_with_npc(
    npc_name: str,
    action: str,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
) -> ActionResult:
    """
    Full NPC interaction flow:
    1. Find NPC by hover text
    2. Verify hover text shows expected NPC
    3. Left-click for default action, or right-click for menu
    """
    # Find the NPC
    target = find_npc_by_hover(npc_name, window_bounds, snapshot_fn)

    if not target:
        return ActionResult(
            intent_id=f"interact_{npc_name}",
            success=False,
            failure_reason="npc_not_found"
        )

    # Check if desired action is the default (first in hover text)
    action_lower = action.lower()
    is_default = False
    if target.actions:
        first_action = target.actions[0].lower()
        if action_lower in first_action:
            is_default = True

    if is_default:
        # Left-click for default action
        click(button='left', dwell_ms=random.randint(45, 85))
    else:
        # Right-click to open menu
        click(button='right', dwell_ms=random.randint(40, 70))
        time.sleep(random.uniform(0.15, 0.25))

        # Find and click the action in the menu
        # Menu appears below cursor, options are ~15px apart
        menu_x = target.screen_x + random.randint(-10, 10)
        menu_y = target.screen_y + 35  # First menu option

        # Scan menu for target action
        for i in range(8):  # Up to 8 menu options
            option_y = menu_y + i * 15
            move_mouse_path(menu_x, option_y, steps=5, curve_strength=0.05)
            time.sleep(0.03)

            snapshot = snapshot_fn()
            hover = get_hover_text(snapshot)

            if action_lower in hover.lower():
                click(button='left', dwell_ms=random.randint(40, 75))
                break

    return ActionResult(
        intent_id=f"interact_{npc_name}_{action}",
        success=True,
        details={"npc": npc_name, "action": action, "pos": (target.screen_x, target.screen_y)}
    )


# =============================================================================
# INVENTORY MANAGEMENT
# =============================================================================

# Inventory grid: 4 columns x 7 rows = 28 slots (0-27)
INVENTORY_COLS = 4
INVENTORY_ROWS = 7
INVENTORY_SLOT_WIDTH = 42
INVENTORY_SLOT_HEIGHT = 36


def get_inventory_slot_position(
    slot: int,
    window_bounds: Tuple[int, int, int, int],
    snapshot: Dict[str, Any],
) -> Tuple[int, int]:
    """
    Get screen coordinates for an inventory slot (0-27).
    """
    win_x, win_y, win_w, win_h = window_bounds

    # Get inventory ROI from snapshot
    roi = snapshot.get("roi", {}).get("fixed", {}).get("inventory", {})
    if roi:
        inv_x = win_x + roi.get("x", 560)
        inv_y = win_y + roi.get("y", 210)
    else:
        # Fallback to approximate position
        inv_x = win_x + 560
        inv_y = win_y + 210

    # Calculate slot position
    col = slot % INVENTORY_COLS
    row = slot // INVENTORY_COLS

    x = inv_x + 20 + col * INVENTORY_SLOT_WIDTH + INVENTORY_SLOT_WIDTH // 2
    y = inv_y + 10 + row * INVENTORY_SLOT_HEIGHT + INVENTORY_SLOT_HEIGHT // 2

    # Add slight randomness within slot
    x += random.randint(-8, 8)
    y += random.randint(-6, 6)

    return (x, y)


def click_inventory_slot(
    slot: int,
    window_bounds: Tuple[int, int, int, int],
    snapshot: Dict[str, Any],
    button: str = 'left',
    shift: bool = False,
) -> ActionResult:
    """
    Click an inventory slot.
    Use shift=True for shift-click (drop) actions.
    """
    if slot < 0 or slot > 27:
        return ActionResult(
            intent_id=f"inv_click_{slot}",
            success=False,
            failure_reason="invalid_slot"
        )

    x, y = get_inventory_slot_position(slot, window_bounds, snapshot)

    move_mouse_path(x, y, steps=10, curve_strength=0.12)
    time.sleep(random.uniform(0.04, 0.10))

    if shift:
        from src.input_exec import key_down, key_up
        key_down('SHIFT')
        time.sleep(0.02)

    click(button=button, dwell_ms=random.randint(40, 75))

    if shift:
        time.sleep(0.02)
        key_up('SHIFT')

    return ActionResult(
        intent_id=f"inv_click_{slot}",
        success=True,
        details={"slot": slot, "pos": (x, y), "shift": shift}
    )


def use_item_on_item(
    source_slot: int,
    target_slot: int,
    window_bounds: Tuple[int, int, int, int],
    snapshot: Dict[str, Any],
) -> ActionResult:
    """
    Use one inventory item on another.
    Click source item, then click target item.
    """
    # Click source item
    result1 = click_inventory_slot(source_slot, window_bounds, snapshot)
    if not result1.success:
        return result1

    time.sleep(random.uniform(0.15, 0.25))

    # Click target item
    result2 = click_inventory_slot(target_slot, window_bounds, snapshot)

    return ActionResult(
        intent_id=f"use_{source_slot}_on_{target_slot}",
        success=result2.success,
        details={"source": source_slot, "target": target_slot}
    )


def drop_item(
    slot: int,
    window_bounds: Tuple[int, int, int, int],
    snapshot: Dict[str, Any],
) -> ActionResult:
    """Drop an item using shift-click."""
    return click_inventory_slot(slot, window_bounds, snapshot, shift=True)


# =============================================================================
# OBJECT INTERACTION
# =============================================================================

def find_object_by_hover(
    target_text: str,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
    scan_area: Optional[Tuple[int, int, int, int]] = None,
    max_positions: int = 30,
) -> Optional[Tuple[int, int]]:
    """
    Find a game object by scanning and checking hover text.
    Returns screen position if found, None otherwise.
    """
    win_x, win_y, win_w, win_h = window_bounds

    if scan_area:
        sx, sy, sw, sh = scan_area
    else:
        # Default: scan game area
        sx = win_x + 50
        sy = win_y + 50
        sw = win_w - 300
        sh = win_h - 250

    target_lower = target_text.lower()

    # Generate scan positions
    positions = []
    step = 60  # Scan every 60 pixels
    for x in range(sx, sx + sw, step):
        for y in range(sy, sy + sh, step):
            positions.append((x + random.randint(-15, 15), y + random.randint(-15, 15)))

    random.shuffle(positions)

    for x, y in positions[:max_positions]:
        # Use smooth, human-like movement during scanning
        move_mouse_path(x, y, steps=20, curve_strength=0.10, step_delay_ms=10)
        time.sleep(0.15)  # Pause to let hover text update

        snapshot = snapshot_fn()
        hover = get_hover_text(snapshot)

        if target_lower in hover.lower():
            return (x, y)

    return None


def interact_with_object(
    object_text: str,
    action: str,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
) -> ActionResult:
    """
    Interact with a game object:
    1. Find object by hover text
    2. Left-click for default action, or right-click for menu
    """
    pos = find_object_by_hover(object_text, window_bounds, snapshot_fn)

    if not pos:
        return ActionResult(
            intent_id=f"interact_{object_text}",
            success=False,
            failure_reason="object_not_found"
        )

    x, y = pos

    # Move back to position in case mouse drifted during snapshot
    move_mouse_path(x, y, steps=15)
    time.sleep(0.1)

    snapshot = snapshot_fn()
    hover = get_hover_text(snapshot)
    actions = parse_hover_actions(hover)

    action_lower = action.lower()
    is_default = actions and action_lower in actions[0].lower()

    if is_default:
        # Ensure we're at target position and click
        click(button='left', dwell_ms=random.randint(60, 100))
    else:
        click(button='right', dwell_ms=random.randint(40, 70))
        time.sleep(random.uniform(0.12, 0.20))

        # Find action in menu
        menu_y = y + 35
        for i in range(8):
            option_y = menu_y + i * 15
            move_mouse_path(x, option_y, steps=4, curve_strength=0.05)
            time.sleep(0.025)

            snapshot = snapshot_fn()
            hover = get_hover_text(snapshot)

            if action_lower in hover.lower():
                click(button='left', dwell_ms=random.randint(40, 70))
                break

    return ActionResult(
        intent_id=f"interact_{object_text}_{action}",
        success=True,
        details={"object": object_text, "action": action, "pos": pos}
    )


# =============================================================================
# WALKING & NAVIGATION
# =============================================================================

def click_minimap(
    dx: int,
    dy: int,
    window_bounds: Tuple[int, int, int, int],
    snapshot: Dict[str, Any],
) -> ActionResult:
    """
    Click on minimap relative to center (player position).
    dx, dy are offsets in pixels from minimap center.
    """
    win_x, win_y, win_w, win_h = window_bounds

    # Get minimap ROI
    roi = snapshot.get("roi", {}).get("fixed", {}).get("minimap", {})
    if roi:
        mm_x = win_x + roi.get("x", 550)
        mm_y = win_y + roi.get("y", 5)
        mm_w = roi.get("width", 150)
        mm_h = roi.get("height", 150)
    else:
        mm_x = win_x + 550
        mm_y = win_y + 5
        mm_w = 150
        mm_h = 150

    # Center of minimap
    center_x = mm_x + mm_w // 2
    center_y = mm_y + mm_h // 2

    # Target position
    target_x = center_x + dx + random.randint(-3, 3)
    target_y = center_y + dy + random.randint(-3, 3)

    # Clamp to minimap bounds
    target_x = max(mm_x + 10, min(mm_x + mm_w - 10, target_x))
    target_y = max(mm_y + 10, min(mm_y + mm_h - 10, target_y))

    move_mouse_path(target_x, target_y, steps=12, curve_strength=0.15)
    time.sleep(random.uniform(0.04, 0.08))
    click(button='left', dwell_ms=random.randint(35, 65))

    return ActionResult(
        intent_id="minimap_click",
        success=True,
        details={"offset": (dx, dy), "pos": (target_x, target_y)}
    )


def rotate_camera(
    direction: str,
    amount: int = 1,
    window_bounds: Tuple[int, int, int, int] = None,
) -> ActionResult:
    """
    Rotate camera using arrow keys.
    direction: 'left', 'right', 'up', 'down'
    amount: number of key presses
    """
    from src.input_exec import press_key_name

    key_map = {
        'left': 'LEFT',
        'right': 'RIGHT',
        'up': 'UP',
        'down': 'DOWN',
    }

    key = key_map.get(direction.lower())
    if not key:
        return ActionResult(
            intent_id="rotate_camera",
            success=False,
            failure_reason="invalid_direction"
        )

    for _ in range(amount):
        hold_ms = random.randint(80, 200)
        press_key_name(key, hold_ms=hold_ms)
        time.sleep(random.uniform(0.05, 0.15))

    return ActionResult(
        intent_id="rotate_camera",
        success=True,
        details={"direction": direction, "amount": amount}
    )


def search_and_click(
    target_text: str,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
    max_rotations: int = 4,
) -> ActionResult:
    """
    Search for a target by rotating camera and scanning.
    Useful when target might be off-screen.
    """
    for rotation in range(max_rotations):
        # Try to find target
        pos = find_object_by_hover(target_text, window_bounds, snapshot_fn, max_positions=20)

        if pos:
            x, y = pos
            click(button='left', dwell_ms=random.randint(45, 80))
            return ActionResult(
                intent_id=f"search_click_{target_text}",
                success=True,
                details={"found_after_rotations": rotation, "pos": pos}
            )

        # Rotate camera and try again
        rotate_camera('right', amount=2)
        time.sleep(random.uniform(0.3, 0.5))

    return ActionResult(
        intent_id=f"search_click_{target_text}",
        success=False,
        failure_reason="not_found_after_rotation"
    )


# =============================================================================
# ERROR RECOVERY
# =============================================================================

class RecoveryStrategy(Enum):
    """Recovery strategies for failed actions"""
    RETRY = "retry"
    ROTATE_AND_RETRY = "rotate_and_retry"
    WALK_AND_RETRY = "walk_and_retry"
    CLOSE_INTERFACE = "close_interface"
    RESET_STATE = "reset_state"


def detect_stuck_state(
    snapshots: List[Dict[str, Any]],
    min_samples: int = 5,
) -> bool:
    """
    Detect if agent is stuck by comparing recent snapshots.
    Returns True if no meaningful change detected.
    """
    if len(snapshots) < min_samples:
        return False

    # Compare last N snapshots
    recent = snapshots[-min_samples:]

    # Check if player position hasn't changed
    positions = []
    for snap in recent:
        derived = snap.get("derived", {})
        loc = derived.get("location", {})
        region = loc.get("region", "unknown")
        positions.append(region)

    # If all positions are identical and unknown, might be stuck
    if len(set(positions)) == 1 and positions[0] == "unknown":
        return True

    # Check hover text - if it's been the same for all snapshots, might be stuck
    hovers = [get_hover_text(s) for s in recent]
    if len(set(hovers)) == 1:
        return True

    return False


def attempt_recovery(
    strategy: RecoveryStrategy,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
) -> ActionResult:
    """
    Attempt to recover from a stuck/failed state.
    """
    if strategy == RecoveryStrategy.ROTATE_AND_RETRY:
        rotate_camera('right', amount=3)
        time.sleep(0.4)
        return ActionResult(intent_id="recovery_rotate", success=True)

    if strategy == RecoveryStrategy.CLOSE_INTERFACE:
        from src.input_exec import press_key_name
        press_key_name('ESCAPE', hold_ms=50)
        time.sleep(0.2)
        return ActionResult(intent_id="recovery_close", success=True)

    if strategy == RecoveryStrategy.WALK_AND_RETRY:
        snapshot = snapshot_fn()
        # Click near center minimap to walk somewhere
        click_minimap(random.randint(-20, 20), random.randint(-20, 20), window_bounds, snapshot)
        time.sleep(1.5)  # Wait for walking
        return ActionResult(intent_id="recovery_walk", success=True)

    return ActionResult(
        intent_id="recovery",
        success=False,
        failure_reason="unknown_strategy"
    )


# =============================================================================
# PATHFINDING WITH WAYPOINTS
# =============================================================================

@dataclass
class Waypoint:
    """A navigation waypoint."""
    minimap_dx: int  # Offset from minimap center
    minimap_dy: int
    description: str = ""
    wait_after: float = 1.5  # Seconds to wait after clicking


def walk_waypoints(
    waypoints: List[Waypoint],
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
    stuck_threshold: int = 3,
) -> ActionResult:
    """
    Walk a path defined by multiple waypoints.
    Each waypoint is a minimap offset from current position.

    Args:
        waypoints: List of waypoints to follow
        window_bounds: Game window bounds
        snapshot_fn: Function to capture game state
        stuck_threshold: Max retries per waypoint before giving up
    """
    for i, wp in enumerate(waypoints):
        retries = 0
        while retries < stuck_threshold:
            snapshot = snapshot_fn()
            result = click_minimap(wp.minimap_dx, wp.minimap_dy, window_bounds, snapshot)

            if not result.success:
                retries += 1
                continue

            # Wait for movement
            time.sleep(wp.wait_after + random.uniform(-0.2, 0.3))

            # Verify we moved (check if player is idle)
            snapshot = snapshot_fn()
            if is_player_moving(snapshot):
                # Still moving, wait more
                time.sleep(0.5)

            break

        if retries >= stuck_threshold:
            return ActionResult(
                intent_id="walk_waypoints",
                success=False,
                failure_reason=f"stuck_at_waypoint_{i}",
                details={"waypoint": i, "description": wp.description}
            )

    return ActionResult(
        intent_id="walk_waypoints",
        success=True,
        details={"waypoints_completed": len(waypoints)}
    )


def is_player_moving(snapshot: Dict[str, Any]) -> bool:
    """Check if player is currently moving (animation/position change)."""
    derived = snapshot.get("derived", {})

    # Check animation state if available
    animation = derived.get("animation", "idle")
    if animation in ["walking", "running"]:
        return True

    # Check RuneLite data if available
    runelite = snapshot.get("runelite", {})
    player = runelite.get("player", {})
    if player.get("is_moving", False):
        return True

    return False


def walk_direction(
    direction: str,
    distance: str,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
) -> ActionResult:
    """
    Walk in a compass direction on the minimap.

    Args:
        direction: 'north', 'south', 'east', 'west', 'ne', 'nw', 'se', 'sw'
        distance: 'short' (20px), 'medium' (40px), 'far' (60px)
        window_bounds: Game window bounds
        snapshot_fn: Snapshot function
    """
    # Direction to minimap offset
    dir_map = {
        'north': (0, -1), 'n': (0, -1),
        'south': (0, 1), 's': (0, 1),
        'east': (1, 0), 'e': (1, 0),
        'west': (-1, 0), 'w': (-1, 0),
        'northeast': (1, -1), 'ne': (1, -1),
        'northwest': (-1, -1), 'nw': (-1, -1),
        'southeast': (1, 1), 'se': (1, 1),
        'southwest': (-1, 1), 'sw': (-1, 1),
    }

    dist_map = {
        'short': 20,
        'medium': 40,
        'far': 60,
        'max': 70,
    }

    dir_vec = dir_map.get(direction.lower(), (0, 0))
    dist_px = dist_map.get(distance.lower(), 40)

    dx = dir_vec[0] * dist_px
    dy = dir_vec[1] * dist_px

    snapshot = snapshot_fn()
    return click_minimap(dx, dy, window_bounds, snapshot)


# =============================================================================
# OBJECT STATE DETECTION
# =============================================================================

@dataclass
class ObjectState:
    """State information about a game object."""
    name: str
    exists: bool = True
    is_depleted: bool = False
    is_interactable: bool = True
    position: Optional[Tuple[int, int]] = None
    last_seen: float = 0.0


def detect_object_state(
    object_name: str,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
    expected_actions: List[str] = None,
) -> ObjectState:
    """
    Detect the current state of a game object.

    Checks if object exists, is depleted (tree stump, empty rock), etc.

    Args:
        object_name: Name to search for in hover text
        window_bounds: Game window bounds
        snapshot_fn: Snapshot function
        expected_actions: Actions that indicate object is usable (e.g., ['Chop', 'Mine'])
    """
    state = ObjectState(name=object_name)

    # Try to find the object
    pos = find_object_by_hover(object_name, window_bounds, snapshot_fn, max_positions=15)

    if not pos:
        state.exists = False
        state.is_interactable = False
        return state

    state.position = pos
    state.last_seen = time.time()

    # Check hover text for actions
    # Move to position and get hover
    x, y = pos
    move_mouse_path(x, y, steps=5, curve_strength=0.05, step_delay_ms=10)
    time.sleep(0.04)

    snapshot = snapshot_fn()
    hover = get_hover_text(snapshot)
    actions = parse_hover_actions(hover)

    # Check if expected actions are available
    if expected_actions:
        has_action = any(
            any(exp.lower() in act.lower() for exp in expected_actions)
            for act in actions
        )
        if not has_action:
            state.is_depleted = True
            state.is_interactable = False

    # Common depleted indicators
    depleted_keywords = ['stump', 'empty', 'depleted', 'rocks', 'nothing']
    hover_lower = hover.lower()
    if any(kw in hover_lower for kw in depleted_keywords):
        state.is_depleted = True
        state.is_interactable = False

    return state


def wait_for_object_respawn(
    object_name: str,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
    expected_actions: List[str],
    max_wait_seconds: float = 30.0,
    check_interval: float = 2.0,
) -> ObjectState:
    """
    Wait for a depleted object to respawn.

    Args:
        object_name: Name of object to wait for
        window_bounds: Game window bounds
        snapshot_fn: Snapshot function
        expected_actions: Actions that indicate object is ready
        max_wait_seconds: Maximum time to wait
        check_interval: Seconds between checks
    """
    start_time = time.time()

    while time.time() - start_time < max_wait_seconds:
        state = detect_object_state(object_name, window_bounds, snapshot_fn, expected_actions)

        if state.exists and state.is_interactable and not state.is_depleted:
            return state

        time.sleep(check_interval)

    # Timeout - return last state
    return ObjectState(name=object_name, exists=False, is_depleted=True)


# =============================================================================
# NPC TRACKING
# =============================================================================

@dataclass
class TrackedNPC:
    """An NPC being tracked over time."""
    name: str
    last_position: Optional[Tuple[int, int]] = None
    last_seen: float = 0.0
    positions_history: List[Tuple[int, int, float]] = field(default_factory=list)
    is_moving: bool = False

    def update_position(self, x: int, y: int):
        """Record new position."""
        now = time.time()
        self.positions_history.append((x, y, now))

        # Keep only last 10 positions
        if len(self.positions_history) > 10:
            self.positions_history.pop(0)

        # Detect if moving
        if self.last_position:
            dx = abs(x - self.last_position[0])
            dy = abs(y - self.last_position[1])
            self.is_moving = dx > 10 or dy > 10

        self.last_position = (x, y)
        self.last_seen = now

    def predict_position(self) -> Optional[Tuple[int, int]]:
        """Predict next position based on movement history."""
        if len(self.positions_history) < 2:
            return self.last_position

        # Simple linear extrapolation from last two positions
        p1 = self.positions_history[-2]
        p2 = self.positions_history[-1]

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]

        # Predict where they'll be
        pred_x = p2[0] + dx
        pred_y = p2[1] + dy

        return (pred_x, pred_y)


def track_npc(
    npc_name: str,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
    track_duration: float = 2.0,
    samples: int = 4,
) -> TrackedNPC:
    """
    Track an NPC's movement over time.

    Args:
        npc_name: Name of NPC to track
        window_bounds: Game window bounds
        snapshot_fn: Snapshot function
        track_duration: Total time to track
        samples: Number of position samples to take
    """
    tracked = TrackedNPC(name=npc_name)
    interval = track_duration / samples

    for _ in range(samples):
        target = find_npc_by_hover(npc_name, window_bounds, snapshot_fn, max_attempts=5)

        if target:
            tracked.update_position(target.screen_x, target.screen_y)

        time.sleep(interval)

    return tracked


def follow_npc(
    npc_name: str,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
    max_follow_time: float = 10.0,
    interact_action: str = "Talk-to",
) -> ActionResult:
    """
    Follow a moving NPC and interact when close enough.

    Args:
        npc_name: Name of NPC to follow
        window_bounds: Game window bounds
        snapshot_fn: Snapshot function
        max_follow_time: Maximum time to spend following
        interact_action: Action to perform when catching up
    """
    start_time = time.time()

    while time.time() - start_time < max_follow_time:
        # Find current position
        target = find_npc_by_hover(npc_name, window_bounds, snapshot_fn, max_attempts=8)

        if not target:
            # Lost sight, rotate camera
            rotate_camera('right', amount=2)
            time.sleep(0.3)
            continue

        # Check if we're close enough (NPC near center of game area)
        win_x, win_y, win_w, win_h = window_bounds
        center_x = win_x + win_w // 2
        center_y = win_y + win_h // 2

        dist_x = abs(target.screen_x - center_x)
        dist_y = abs(target.screen_y - center_y)

        if dist_x < 100 and dist_y < 100:
            # Close enough - interact
            result = interact_with_npc(npc_name, interact_action, window_bounds, snapshot_fn)
            return result

        # Too far - click on NPC to walk toward them
        move_mouse_path(target.screen_x, target.screen_y, steps=8)
        click(button='left', dwell_ms=random.randint(40, 70))
        time.sleep(random.uniform(1.0, 1.5))

    return ActionResult(
        intent_id=f"follow_{npc_name}",
        success=False,
        failure_reason="follow_timeout"
    )


# =============================================================================
# INTERACTION VALIDATION
# =============================================================================

def validate_interaction(
    expected_change: str,
    snapshot_before: Dict[str, Any],
    snapshot_fn: Callable[[], Dict[str, Any]],
    timeout: float = 3.0,
) -> bool:
    """
    Validate that an interaction had the expected effect.

    Args:
        expected_change: What to look for:
            - 'dialogue_opened': Check if dialogue is now open
            - 'inventory_changed': Check if inventory changed
            - 'player_animating': Check if player is doing an action
            - 'hover_changed': Check if hover text changed
        snapshot_before: Snapshot taken before the action
        snapshot_fn: Function to capture current state
        timeout: Max time to wait for change
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        snapshot_after = snapshot_fn()

        if expected_change == 'dialogue_opened':
            dialogue = detect_dialogue_state(snapshot_after)
            if dialogue.state != DialogueState.NONE:
                return True

        elif expected_change == 'inventory_changed':
            # Compare inventory snapshots
            inv_before = snapshot_before.get("runelite", {}).get("inventory", [])
            inv_after = snapshot_after.get("runelite", {}).get("inventory", [])
            if inv_before != inv_after:
                return True

        elif expected_change == 'player_animating':
            if is_player_moving(snapshot_after):
                return True
            # Check for skill animations
            derived = snapshot_after.get("derived", {})
            if derived.get("animation", "idle") != "idle":
                return True

        elif expected_change == 'hover_changed':
            hover_before = get_hover_text(snapshot_before)
            hover_after = get_hover_text(snapshot_after)
            if hover_before != hover_after:
                return True

        time.sleep(0.2)

    return False


def interact_and_validate(
    target_text: str,
    action: str,
    expected_change: str,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
    max_retries: int = 3,
) -> ActionResult:
    """
    Interact with an object/NPC and validate the result.
    Retries if validation fails.

    Args:
        target_text: Name/text of target
        action: Action to perform
        expected_change: Expected result type
        window_bounds: Game window bounds
        snapshot_fn: Snapshot function
        max_retries: Max retry attempts
    """
    for attempt in range(max_retries):
        snapshot_before = snapshot_fn()

        # Try object interaction first
        result = interact_with_object(target_text, action, window_bounds, snapshot_fn)

        if not result.success:
            # Try NPC interaction
            result = interact_with_npc(target_text, action, window_bounds, snapshot_fn)

        if not result.success:
            continue

        # Validate the interaction worked
        if validate_interaction(expected_change, snapshot_before, snapshot_fn):
            result.details["validated"] = True
            return result

        # Validation failed, retry
        time.sleep(random.uniform(0.3, 0.6))

    return ActionResult(
        intent_id=f"interact_validate_{target_text}",
        success=False,
        failure_reason="validation_failed",
        details={"attempts": max_retries}
    )


# =============================================================================
# INVENTORY BY HOVER (without RuneLite data)
# =============================================================================

def scan_inventory_slots(
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
    slots_to_scan: Optional[List[int]] = None,
) -> Dict[int, str]:
    """
    Scan inventory slots by hovering and reading hover text.
    Works without RuneLite data.

    Args:
        window_bounds: Game window bounds
        snapshot_fn: Snapshot function
        slots_to_scan: Specific slots to scan (0-27), or None for all

    Returns:
        Dict mapping slot number to item name (empty string if empty)
    """
    results = {}

    if slots_to_scan is None:
        slots_to_scan = list(range(28))

    snapshot = snapshot_fn()

    for slot in slots_to_scan:
        pos = get_inventory_slot_position(slot, window_bounds, snapshot)
        if not pos:
            continue

        x, y = pos
        move_mouse_path(x, y, steps=4, curve_strength=0.03, step_delay_ms=10)
        time.sleep(0.04)

        snap = snapshot_fn()
        hover = get_hover_text(snap)

        # Parse item name from hover text
        # Format is usually "Action Item" or just "Item"
        if hover and not hover.lower().startswith(('walk', 'cancel')):
            # Remove common action prefixes
            item_name = hover
            for prefix in ['Use ', 'Drop ', 'Examine ', 'Eat ', 'Drink ', 'Equip ', 'Wield ']:
                if hover.startswith(prefix):
                    item_name = hover[len(prefix):]
                    break
            results[slot] = item_name
        else:
            results[slot] = ""

    return results


def find_item_slot_by_hover(
    item_name: str,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
) -> Optional[int]:
    """
    Find an item in inventory by hovering over slots.
    Returns slot number (0-27) or None if not found.
    """
    inventory = scan_inventory_slots(window_bounds, snapshot_fn)

    item_lower = item_name.lower()
    for slot, name in inventory.items():
        if item_lower in name.lower():
            return slot

    return None


# =============================================================================
# DOOR/GATE AUTO-OPEN
# =============================================================================

DOOR_KEYWORDS = ['door', 'gate', 'fence', 'barrier', 'entrance']
OPEN_ACTIONS = ['open', 'push', 'enter', 'go-through', 'pass']


def detect_blocking_door(
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
    search_radius: int = 100,
) -> Optional[Tuple[int, int, str]]:
    """
    Detect if there's a door/gate blocking the player's path.
    Scans near the center of the game view.

    Returns (x, y, door_text) if found, None otherwise.
    """
    win_x, win_y, win_w, win_h = window_bounds

    # Search area near center (where player would walk into a door)
    center_x = win_x + win_w // 2
    center_y = win_y + win_h // 2

    # Scan in front of player (assume facing roughly center)
    scan_positions = [
        (center_x, center_y - 50),      # North
        (center_x + 50, center_y),      # East
        (center_x, center_y + 50),      # South
        (center_x - 50, center_y),      # West
        (center_x + 40, center_y - 40), # NE
        (center_x - 40, center_y - 40), # NW
        (center_x + 40, center_y + 40), # SE
        (center_x - 40, center_y + 40), # SW
    ]

    for x, y in scan_positions:
        # Add some randomness
        x += random.randint(-10, 10)
        y += random.randint(-10, 10)

        move_mouse_path(x, y, steps=5, curve_strength=0.05, step_delay_ms=10)
        time.sleep(0.03)

        snapshot = snapshot_fn()
        hover = get_hover_text(snapshot).lower()

        # Check if it's a door/gate
        for keyword in DOOR_KEYWORDS:
            if keyword in hover:
                # Check if it has an open action
                for action in OPEN_ACTIONS:
                    if action in hover:
                        return (x, y, hover)

    return None


def try_open_door(
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
) -> ActionResult:
    """
    Try to find and open a nearby door/gate.
    """
    door_info = detect_blocking_door(window_bounds, snapshot_fn)

    if not door_info:
        return ActionResult(
            intent_id="open_door",
            success=False,
            failure_reason="no_door_found"
        )

    x, y, hover_text = door_info

    # Move to door and click
    move_mouse_path(x, y, steps=6, curve_strength=0.08)
    time.sleep(0.03)

    # Check if "Open" is the default action
    if hover_text.startswith('open'):
        click(button='left', dwell_ms=random.randint(40, 70))
    else:
        # Right-click for menu
        click(button='right', dwell_ms=random.randint(35, 60))
        time.sleep(0.15)

        # Find "Open" in menu
        for i in range(5):
            menu_y = y + 35 + i * 15
            move_mouse_path(x, menu_y, steps=4)
            time.sleep(0.03)

            snap = snapshot_fn()
            menu_hover = get_hover_text(snap).lower()
            if 'open' in menu_hover:
                click(button='left', dwell_ms=random.randint(40, 65))
                break

    time.sleep(0.5)  # Wait for door to open

    return ActionResult(
        intent_id="open_door",
        success=True,
        details={"door": hover_text, "pos": (x, y)}
    )


def walk_with_door_handling(
    dx: int,
    dy: int,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
    max_door_attempts: int = 2,
) -> ActionResult:
    """
    Walk to a position, automatically opening doors if blocked.
    """
    snapshot = snapshot_fn()

    for attempt in range(max_door_attempts + 1):
        # Try to walk
        result = click_minimap(dx, dy, window_bounds, snapshot)
        time.sleep(1.0)  # Wait for movement

        # Check if we're stuck (might be a door)
        new_snapshot = snapshot_fn()
        if is_player_moving(new_snapshot):
            return result  # Successfully moving

        # Check for blocking door
        door = detect_blocking_door(window_bounds, snapshot_fn)
        if door:
            try_open_door(window_bounds, snapshot_fn)
            time.sleep(0.5)
        else:
            # No door, might be stuck for another reason
            break

    return result


# =============================================================================
# STUCK DETECTION & AUTO-UNSTICK
# =============================================================================

@dataclass
class StuckState:
    """Tracking state for stuck detection."""
    position_samples: List[Tuple[str, float]] = field(default_factory=list)
    action_history: List[str] = field(default_factory=list)
    stuck_count: int = 0
    last_unstick_time: float = 0.0

    def add_sample(self, location: str, timestamp: float):
        self.position_samples.append((location, timestamp))
        if len(self.position_samples) > 10:
            self.position_samples.pop(0)

    def add_action(self, action: str):
        self.action_history.append(action)
        if len(self.action_history) > 20:
            self.action_history.pop(0)

    def is_stuck(self, min_samples: int = 5, max_unique: int = 2) -> bool:
        """Check if stuck based on position history."""
        if len(self.position_samples) < min_samples:
            return False

        recent = [p[0] for p in self.position_samples[-min_samples:]]
        unique_positions = set(recent)

        return len(unique_positions) <= max_unique

    def is_action_loop(self, min_repeat: int = 4) -> bool:
        """Check if repeating the same action."""
        if len(self.action_history) < min_repeat:
            return False

        recent = self.action_history[-min_repeat:]
        return len(set(recent)) == 1


def auto_unstick(
    stuck_state: StuckState,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
) -> ActionResult:
    """
    Try various strategies to get unstuck.
    """
    stuck_state.stuck_count += 1
    stuck_state.last_unstick_time = time.time()

    strategy = stuck_state.stuck_count % 5

    if strategy == 0:
        # Walk in random direction
        dx = random.randint(-50, 50)
        dy = random.randint(-50, 50)
        snapshot = snapshot_fn()
        click_minimap(dx, dy, window_bounds, snapshot)
        time.sleep(1.5)
        return ActionResult(intent_id="unstick", success=True, details={"strategy": "random_walk"})

    elif strategy == 1:
        # Rotate camera
        rotate_camera(random.choice(['left', 'right']), amount=3)
        time.sleep(0.5)
        return ActionResult(intent_id="unstick", success=True, details={"strategy": "rotate"})

    elif strategy == 2:
        # Try opening a door
        result = try_open_door(window_bounds, snapshot_fn)
        if result.success:
            return ActionResult(intent_id="unstick", success=True, details={"strategy": "open_door"})
        return ActionResult(intent_id="unstick", success=True, details={"strategy": "door_attempt"})

    elif strategy == 3:
        # Click center of screen (might unstick from dialogue/interface)
        from src.input_exec import press_key_name
        press_key_name('ESCAPE', hold_ms=50)
        time.sleep(0.2)
        return ActionResult(intent_id="unstick", success=True, details={"strategy": "escape"})

    else:
        # Walk backwards (opposite of recent movement)
        snapshot = snapshot_fn()
        click_minimap(-30, 30, window_bounds, snapshot)  # Walk south-west
        time.sleep(1.5)
        return ActionResult(intent_id="unstick", success=True, details={"strategy": "walk_back"})


# =============================================================================
# EQUIPMENT MANAGEMENT
# =============================================================================

# Equipment slot positions relative to equipment tab
EQUIPMENT_SLOTS = {
    'head': (0, 0),
    'cape': (-1, 1),
    'neck': (0, 1),
    'ammo': (1, 1),
    'weapon': (-1, 2),
    'body': (0, 2),
    'shield': (1, 2),
    'legs': (0, 3),
    'hands': (-1, 4),
    'feet': (0, 4),
    'ring': (1, 4),
}


def open_equipment_tab(
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
) -> bool:
    """Open the equipment/worn items tab."""
    from src.input_exec import press_key_name

    # F4 opens equipment tab in default keybinds
    press_key_name('F4', hold_ms=50)
    time.sleep(0.2)

    # Verify tab is open
    snapshot = snapshot_fn()
    ui = snapshot.get("ui", {})
    return ui.get("active_tab") == "equipment"


def get_equipment_slot_position(
    slot_name: str,
    window_bounds: Tuple[int, int, int, int],
    snapshot: Dict[str, Any],
) -> Optional[Tuple[int, int]]:
    """Get screen position of an equipment slot."""
    if slot_name not in EQUIPMENT_SLOTS:
        return None

    win_x, win_y, win_w, win_h = window_bounds

    # Equipment panel is in the right sidebar
    # Approximate positions (will need calibration)
    panel_x = win_x + win_w - 200
    panel_y = win_y + 240

    slot_offset = EQUIPMENT_SLOTS[slot_name]
    slot_width = 40
    slot_height = 36

    x = panel_x + 85 + slot_offset[0] * slot_width
    y = panel_y + slot_offset[1] * slot_height

    return (x, y)


def equip_item(
    item_name: str,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
) -> ActionResult:
    """
    Equip an item from inventory.
    """
    # Find item in inventory
    slot = find_item_slot_by_hover(item_name, window_bounds, snapshot_fn)

    if slot is None:
        return ActionResult(
            intent_id=f"equip_{item_name}",
            success=False,
            failure_reason="item_not_found"
        )

    # Click the item to equip (most items equip on left-click)
    snapshot = snapshot_fn()
    pos = get_inventory_slot_position(slot, window_bounds, snapshot)

    if pos:
        x, y = pos
        move_mouse_path(x, y, steps=6, curve_strength=0.08)
        time.sleep(0.03)

        # Check if equip/wear/wield is default action
        snap = snapshot_fn()
        hover = get_hover_text(snap).lower()

        if any(action in hover for action in ['equip', 'wear', 'wield']):
            click(button='left', dwell_ms=random.randint(45, 75))
        else:
            # Right-click for menu
            click(button='right', dwell_ms=random.randint(40, 65))
            time.sleep(0.15)

            for i in range(6):
                menu_y = y + 35 + i * 15
                move_mouse_path(x, menu_y, steps=4)
                time.sleep(0.03)

                snap = snapshot_fn()
                menu_hover = get_hover_text(snap).lower()
                if any(action in menu_hover for action in ['equip', 'wear', 'wield']):
                    click(button='left', dwell_ms=random.randint(40, 70))
                    break

        return ActionResult(
            intent_id=f"equip_{item_name}",
            success=True,
            details={"item": item_name, "slot": slot}
        )

    return ActionResult(
        intent_id=f"equip_{item_name}",
        success=False,
        failure_reason="could_not_click"
    )


def unequip_item(
    slot_name: str,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
) -> ActionResult:
    """
    Unequip an item from an equipment slot.
    """
    # Open equipment tab first
    open_equipment_tab(window_bounds, snapshot_fn)
    time.sleep(0.2)

    snapshot = snapshot_fn()
    pos = get_equipment_slot_position(slot_name, window_bounds, snapshot)

    if not pos:
        return ActionResult(
            intent_id=f"unequip_{slot_name}",
            success=False,
            failure_reason="invalid_slot"
        )

    x, y = pos
    move_mouse_path(x, y, steps=6, curve_strength=0.08)
    time.sleep(0.03)

    # Check if slot has an item
    snap = snapshot_fn()
    hover = get_hover_text(snap)

    if not hover or 'empty' in hover.lower():
        return ActionResult(
            intent_id=f"unequip_{slot_name}",
            success=False,
            failure_reason="slot_empty"
        )

    # Click to unequip
    click(button='left', dwell_ms=random.randint(45, 75))

    return ActionResult(
        intent_id=f"unequip_{slot_name}",
        success=True,
        details={"slot": slot_name, "item": hover}
    )


# =============================================================================
# LOGIN/LOGOUT STATE HANDLING
# =============================================================================

class LoginState(Enum):
    """Current login state."""
    LOGGED_IN = "logged_in"
    LOGIN_SCREEN = "login_screen"
    LOBBY = "lobby"
    DISCONNECTED = "disconnected"
    UNKNOWN = "unknown"


# Keywords that indicate login screen
LOGIN_SCREEN_KEYWORDS = [
    'existing user', 'new user', 'login', 'password',
    'enter your username', 'click here to play',
    'welcome to', 'old school runescape'
]

# Keywords that indicate in-game
IN_GAME_KEYWORDS = [
    'inventory', 'attack', 'skills', 'quest', 'prayer',
    'magic', 'combat', 'options', 'logout'
]

# Keywords that indicate disconnection
DISCONNECT_KEYWORDS = [
    'connection lost', 'please wait', 'attempting to reestablish',
    'login server', 'your session has ended', 'disconnected'
]


def detect_login_state(snapshot: Dict[str, Any]) -> LoginState:
    """
    Detect current login state from snapshot.
    """
    if not snapshot:
        return LoginState.UNKNOWN

    ui = snapshot.get("ui", {})
    ocr = snapshot.get("ocr", [])

    # Collect all text from OCR
    all_text = ""
    for item in ocr:
        if isinstance(item, dict):
            all_text += " " + item.get("text", "").lower()
        elif isinstance(item, str):
            all_text += " " + item.lower()

    # Also check hover text
    hover = ui.get("hover_text", "").lower()
    all_text += " " + hover

    # Check for disconnect indicators first (highest priority)
    if any(kw in all_text for kw in DISCONNECT_KEYWORDS):
        return LoginState.DISCONNECTED

    # Check for login screen
    if any(kw in all_text for kw in LOGIN_SCREEN_KEYWORDS):
        return LoginState.LOGIN_SCREEN

    # Check for in-game indicators
    if any(kw in all_text for kw in IN_GAME_KEYWORDS):
        return LoginState.LOGGED_IN

    # Check tabs - if we can see game tabs, we're logged in
    tabs = ui.get("tabs", {})
    if tabs and any(tabs.values()):
        return LoginState.LOGGED_IN

    return LoginState.UNKNOWN


def wait_for_login(
    snapshot_fn: Callable[[], Dict[str, Any]],
    timeout: float = 60.0,
    poll_interval: float = 1.0,
) -> bool:
    """
    Wait for the game to reach logged-in state.
    Returns True if logged in within timeout, False otherwise.
    """
    start = time.time()
    while time.time() - start < timeout:
        snapshot = snapshot_fn()
        state = detect_login_state(snapshot)

        if state == LoginState.LOGGED_IN:
            return True

        time.sleep(poll_interval)

    return False


def handle_disconnect(
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
    max_wait: float = 30.0,
) -> ActionResult:
    """
    Handle a disconnection by waiting for reconnection or login screen.
    """
    start = time.time()

    while time.time() - start < max_wait:
        snapshot = snapshot_fn()
        state = detect_login_state(snapshot)

        if state == LoginState.LOGGED_IN:
            return ActionResult(
                intent_id="handle_disconnect",
                success=True,
                details={"result": "reconnected"}
            )

        if state == LoginState.LOGIN_SCREEN:
            return ActionResult(
                intent_id="handle_disconnect",
                success=False,
                failure_reason="need_login",
                details={"result": "at_login_screen"}
            )

        time.sleep(1.0)

    return ActionResult(
        intent_id="handle_disconnect",
        success=False,
        failure_reason="timeout"
    )


# =============================================================================
# CLICK VERIFICATION AND RETRY
# =============================================================================

def click_with_verify(
    x: int,
    y: int,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
    expected_hover: Optional[str] = None,
    expected_change: Optional[str] = None,
    max_retries: int = 3,
    button: str = 'left',
) -> ActionResult:
    """
    Click a location with verification and retry.

    Args:
        x, y: Click coordinates
        expected_hover: If provided, verify hover text contains this before clicking
        expected_change: If provided, verify something changed after clicking
        max_retries: Number of retry attempts
        button: Mouse button to use
    """
    wx, wy, ww, wh = window_bounds

    for attempt in range(max_retries):
        # Add small random offset on retries to avoid exact same click
        jitter_x = random.randint(-3, 3) if attempt > 0 else 0
        jitter_y = random.randint(-3, 3) if attempt > 0 else 0
        target_x = x + jitter_x
        target_y = y + jitter_y

        # Move to target
        move_mouse_path(target_x, target_y, steps=random.randint(6, 10))
        time.sleep(0.05)

        # Verify hover text if expected
        if expected_hover:
            snapshot = snapshot_fn()
            hover = get_hover_text(snapshot).lower()

            if expected_hover.lower() not in hover:
                # Missed target - try slight re-aim
                time.sleep(0.1)
                # Spiral search pattern around target
                for offset in [(0, -5), (5, 0), (0, 5), (-5, 0), (-5, -5), (5, 5)]:
                    move_mouse_path(target_x + offset[0], target_y + offset[1], steps=3)
                    time.sleep(0.03)
                    snap = snapshot_fn()
                    if expected_hover.lower() in get_hover_text(snap).lower():
                        break
                else:
                    continue  # Try next attempt

        # Capture state before click for change detection
        pre_state = None
        if expected_change:
            pre_snapshot = snapshot_fn()
            pre_state = _extract_state_hash(pre_snapshot, expected_change)

        # Perform click
        click(button=button, dwell_ms=random.randint(40, 70))
        time.sleep(0.15)

        # Verify change occurred if expected
        if expected_change and pre_state:
            post_snapshot = snapshot_fn()
            post_state = _extract_state_hash(post_snapshot, expected_change)

            if pre_state == post_state:
                # No change detected - click may have missed
                continue

        return ActionResult(
            intent_id=f"click_verify_{x}_{y}",
            success=True,
            details={"attempts": attempt + 1, "x": target_x, "y": target_y}
        )

    return ActionResult(
        intent_id=f"click_verify_{x}_{y}",
        success=False,
        failure_reason="max_retries_exceeded",
        details={"attempts": max_retries}
    )


def _extract_state_hash(snapshot: Dict[str, Any], state_type: str) -> str:
    """Extract a hashable state for change detection."""
    if state_type == "dialogue":
        ui = snapshot.get("ui", {})
        return str(ui.get("dialogue_options", []))

    if state_type == "inventory":
        ui = snapshot.get("ui", {})
        return str(ui.get("inventory", []))

    if state_type == "position":
        player = snapshot.get("player", {})
        return f"{player.get('x', 0)},{player.get('y', 0)}"

    if state_type == "hover":
        ui = snapshot.get("ui", {})
        return ui.get("hover_text", "")

    # Default: hash the whole UI state
    return str(snapshot.get("ui", {}))


# =============================================================================
# INVENTORY FULL HANDLING
# =============================================================================

class InventoryFullStrategy(Enum):
    """Strategy when inventory is full."""
    DROP_JUNK = "drop_junk"
    BANK_TRIP = "bank_trip"
    STOP = "stop"
    CONTINUE = "continue"  # For activities that don't need inventory space


# Items that are safe to drop when inventory is full
DROPPABLE_JUNK = [
    'bones', 'ashes', 'burnt', 'junk', 'rock', 'empty vial',
    'empty pot', 'empty bucket', 'empty jug'
]


def detect_inventory_full(snapshot: Dict[str, Any]) -> bool:
    """Check if inventory is full."""
    ui = snapshot.get("ui", {})
    inventory = ui.get("inventory", [])

    if inventory:
        # Count filled slots
        filled = sum(1 for item in inventory if item and item.get("name"))
        return filled >= 28

    # Fallback: check OCR for "full" message
    ocr = snapshot.get("ocr", [])
    for item in ocr:
        text = item.get("text", "").lower() if isinstance(item, dict) else str(item).lower()
        if "inventory" in text and "full" in text:
            return True

    return False


def handle_inventory_full(
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
    strategy: InventoryFullStrategy = InventoryFullStrategy.DROP_JUNK,
    bank_callback: Optional[Callable[[], bool]] = None,
) -> ActionResult:
    """
    Handle a full inventory based on the chosen strategy.

    Args:
        window_bounds: Game window bounds
        snapshot_fn: Function to get current game state
        strategy: How to handle the full inventory
        bank_callback: Optional callback to execute bank trip
    """
    if strategy == InventoryFullStrategy.CONTINUE:
        return ActionResult(
            intent_id="inv_full_continue",
            success=True,
            details={"strategy": "continue"}
        )

    if strategy == InventoryFullStrategy.STOP:
        return ActionResult(
            intent_id="inv_full_stop",
            success=False,
            failure_reason="inventory_full_stop",
            details={"strategy": "stop"}
        )

    if strategy == InventoryFullStrategy.DROP_JUNK:
        dropped = 0
        snapshot = snapshot_fn()
        inventory = snapshot.get("ui", {}).get("inventory", [])

        for slot, item in enumerate(inventory):
            if not item:
                continue

            item_name = item.get("name", "").lower()
            if any(junk in item_name for junk in DROPPABLE_JUNK):
                # Drop this item
                result = drop_inventory_slot(slot, window_bounds)
                if result.success:
                    dropped += 1
                time.sleep(0.1)

        if dropped > 0:
            return ActionResult(
                intent_id="inv_full_drop",
                success=True,
                details={"dropped": dropped, "strategy": "drop_junk"}
            )
        else:
            # No junk to drop - fall through to bank or stop
            if bank_callback:
                strategy = InventoryFullStrategy.BANK_TRIP
            else:
                return ActionResult(
                    intent_id="inv_full_no_junk",
                    success=False,
                    failure_reason="no_droppable_junk"
                )

    if strategy == InventoryFullStrategy.BANK_TRIP:
        if bank_callback:
            success = bank_callback()
            return ActionResult(
                intent_id="inv_full_bank",
                success=success,
                details={"strategy": "bank_trip"}
            )
        else:
            return ActionResult(
                intent_id="inv_full_bank",
                success=False,
                failure_reason="no_bank_callback"
            )

    return ActionResult(
        intent_id="inv_full_unknown",
        success=False,
        failure_reason="unknown_strategy"
    )


def drop_inventory_slot(
    slot: int,
    window_bounds: Tuple[int, int, int, int],
    shift_click: bool = True,
) -> ActionResult:
    """Drop an item from inventory using shift-click."""
    from src.input_exec import key_down, key_up

    pos = get_inventory_slot_position(slot, window_bounds)
    if not pos:
        return ActionResult(
            intent_id=f"drop_slot_{slot}",
            success=False,
            failure_reason="invalid_slot"
        )

    x, y = pos
    move_mouse_path(x, y, steps=6)
    time.sleep(0.03)

    if shift_click:
        key_down('shift')
        time.sleep(0.02)
        click(button='left', dwell_ms=random.randint(40, 65))
        time.sleep(0.02)
        key_up('shift')
    else:
        # Right-click drop
        click(button='right', dwell_ms=random.randint(40, 65))
        time.sleep(0.15)
        # Find and click "Drop" option (usually 5th option)
        move_mouse_path(x, y + 75, steps=4)
        time.sleep(0.03)
        click(button='left', dwell_ms=random.randint(40, 65))

    return ActionResult(
        intent_id=f"drop_slot_{slot}",
        success=True,
        details={"slot": slot}
    )


# =============================================================================
# RESET TO KNOWN STATE
# =============================================================================

def reset_to_known_state(
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
    max_attempts: int = 5,
) -> ActionResult:
    """
    Attempt to reset the game to a known, clean state.

    This closes all open interfaces, clears dialogue, and returns
    to the default game view.
    """
    from src.input_exec import press_key

    actions_taken = []

    for attempt in range(max_attempts):
        snapshot = snapshot_fn()
        ui = snapshot.get("ui", {})

        # Check if we're in a clean state
        open_interface = ui.get("open_interface", "none")
        dialogue_options = ui.get("dialogue_options", [])
        in_dialogue = len(dialogue_options) > 0

        if open_interface == "none" and not in_dialogue:
            # Clean state achieved
            return ActionResult(
                intent_id="reset_state",
                success=True,
                details={"attempts": attempt + 1, "actions": actions_taken}
            )

        # Try to close things
        if in_dialogue or open_interface not in ["none", "inventory"]:
            # Press ESC to close
            press_key('escape')
            actions_taken.append("escape")
            time.sleep(0.3)
            continue

        # Click away from any open interface
        wx, wy, ww, wh = window_bounds
        safe_x = wx + ww // 2
        safe_y = wy + wh // 2

        move_mouse_path(safe_x, safe_y, steps=6)
        time.sleep(0.05)
        click(button='left', dwell_ms=random.randint(40, 60))
        actions_taken.append("click_center")
        time.sleep(0.3)

    return ActionResult(
        intent_id="reset_state",
        success=False,
        failure_reason="could_not_reset",
        details={"attempts": max_attempts, "actions": actions_taken}
    )


# =============================================================================
# POST-ACTION VERIFICATION
# =============================================================================

@dataclass
class ActionVerification:
    """Configuration for post-action verification."""
    check_type: str  # "hover_changed", "dialogue_opened", "inventory_changed", etc.
    expected_value: Optional[str] = None  # Expected new value
    timeout: float = 2.0
    poll_interval: float = 0.2


def verify_action_result(
    snapshot_fn: Callable[[], Dict[str, Any]],
    verification: ActionVerification,
    pre_snapshot: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Verify that an action had the expected result.

    Args:
        snapshot_fn: Function to get current game state
        verification: What to verify
        pre_snapshot: State before action (for change detection)
    """
    start = time.time()

    while time.time() - start < verification.timeout:
        snapshot = snapshot_fn()
        ui = snapshot.get("ui", {})

        if verification.check_type == "hover_changed":
            current_hover = ui.get("hover_text", "")
            if pre_snapshot:
                old_hover = pre_snapshot.get("ui", {}).get("hover_text", "")
                if current_hover != old_hover:
                    return True
            elif verification.expected_value:
                if verification.expected_value.lower() in current_hover.lower():
                    return True

        elif verification.check_type == "dialogue_opened":
            options = ui.get("dialogue_options", [])
            if options and len(options) > 0:
                return True

        elif verification.check_type == "dialogue_closed":
            options = ui.get("dialogue_options", [])
            if not options or len(options) == 0:
                return True

        elif verification.check_type == "inventory_changed":
            current_inv = str(ui.get("inventory", []))
            if pre_snapshot:
                old_inv = str(pre_snapshot.get("ui", {}).get("inventory", []))
                if current_inv != old_inv:
                    return True

        elif verification.check_type == "interface_opened":
            interface = ui.get("open_interface", "none")
            if verification.expected_value:
                if interface == verification.expected_value:
                    return True
            else:
                if interface != "none":
                    return True

        elif verification.check_type == "interface_closed":
            interface = ui.get("open_interface", "none")
            if interface == "none":
                return True

        elif verification.check_type == "position_changed":
            player = snapshot.get("player", {})
            current_pos = (player.get("x", 0), player.get("y", 0))
            if pre_snapshot:
                old_player = pre_snapshot.get("player", {})
                old_pos = (old_player.get("x", 0), old_player.get("y", 0))
                if current_pos != old_pos:
                    return True

        time.sleep(verification.poll_interval)

    return False


def execute_with_verification(
    action_fn: Callable[[], ActionResult],
    snapshot_fn: Callable[[], Dict[str, Any]],
    verification: ActionVerification,
    max_retries: int = 3,
) -> ActionResult:
    """
    Execute an action with post-execution verification and retry.

    Args:
        action_fn: The action to execute
        snapshot_fn: Function to get game state
        verification: How to verify success
        max_retries: Number of retry attempts
    """
    for attempt in range(max_retries):
        # Capture pre-action state
        pre_snapshot = snapshot_fn()

        # Execute the action
        result = action_fn()

        if not result.success:
            # Action itself failed - retry
            time.sleep(0.2)
            continue

        # Verify the action had effect
        if verify_action_result(snapshot_fn, verification, pre_snapshot):
            result.details = result.details or {}
            result.details["verified"] = True
            result.details["attempts"] = attempt + 1
            return result

        # Verification failed - action didn't have expected effect
        time.sleep(0.3)

    # All retries exhausted
    return ActionResult(
        intent_id=result.intent_id if result else "unknown",
        success=False,
        failure_reason="verification_failed",
        details={"attempts": max_retries}
    )
