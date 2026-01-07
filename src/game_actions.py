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
from src.input_exec import move_mouse_path, click, get_cursor_pos


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
            move_mouse_path(x, y, steps=8, curve_strength=0.1, step_delay_ms=2)
            time.sleep(0.04)  # Brief pause to let hover text update

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
        move_mouse_path(x, y, steps=6, curve_strength=0.08, step_delay_ms=2)
        time.sleep(0.035)

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
    snapshot = snapshot_fn()
    hover = get_hover_text(snapshot)
    actions = parse_hover_actions(hover)

    action_lower = action.lower()
    is_default = actions and action_lower in actions[0].lower()

    if is_default:
        click(button='left', dwell_ms=random.randint(45, 80))
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
    move_mouse_path(x, y, steps=5, curve_strength=0.05, step_delay_ms=2)
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
        move_mouse_path(x, y, steps=4, curve_strength=0.03, step_delay_ms=2)
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

        move_mouse_path(x, y, steps=5, curve_strength=0.05, step_delay_ms=2)
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
