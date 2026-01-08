"""
Agent Command Interface - Simple commands for the local model.

This module provides a clean, simple API that the local model can use
to issue high-level commands. The model doesn't need to understand
pixels, coordinates, or timing - just issue commands like:
  - "talk_to Survival Expert"
  - "chop Tree"
  - "fish Fishing spot"
  - "walk_to Door"
  - "bank"
  - "eat"

The guardrails and implementation details are handled by the underlying systems.
"""
from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.game_actions import (
    interact_with_npc,
    interact_with_object,
    click_dialogue_continue,
    select_dialogue_by_text,
    detect_dialogue_state,
    DialogueState,
    click_inventory_slot,
    drop_item,
    click_minimap,
    rotate_camera,
    # Keyboard-based dialogue (faster)
    press_dialogue_continue,
    press_dialogue_option,
    handle_dialogue_keyboard,
    # Chat logging
    get_chat_logger,
    search_and_click,
    get_hover_text,
    # New pathfinding and tracking
    walk_direction,
    walk_waypoints,
    Waypoint,
    follow_npc,
    track_npc,
    # Object state
    detect_object_state,
    wait_for_object_respawn,
    # Inventory by hover
    find_item_slot_by_hover,
    scan_inventory_slots,
    # Validation
    interact_and_validate,
    validate_interaction,
)
from src.autonomy import (
    SkillingLoop,
    SkillingConfig,
    WOODCUTTING_CONFIG,
    FISHING_CONFIG,
    MINING_CONFIG,
    CombatLoop,
    CombatConfig,
    BankTrip,
    open_bank,
    deposit_all,
    close_bank,
    detect_bank_open,
    detect_random_event,
    handle_random_event,
    is_inventory_full,
    find_item_in_inventory,
    parse_inventory_from_runelite,
    get_health_percent,
)


# =============================================================================
# COMMAND TYPES
# =============================================================================

class CommandType(Enum):
    """Types of commands the model can issue."""
    # Interaction
    TALK_TO = "talk_to"
    CLICK = "click"
    USE = "use"

    # Skilling
    CHOP = "chop"
    FISH = "fish"
    MINE = "mine"
    COOK = "cook"

    # Combat
    ATTACK = "attack"
    EAT = "eat"
    FLEE = "flee"

    # Navigation
    WALK_TO = "walk_to"
    OPEN = "open"
    ENTER = "enter"

    # Banking
    BANK = "bank"
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"

    # Dialogue
    CONTINUE = "continue"
    SELECT = "select"

    # Utility
    WAIT = "wait"
    ROTATE = "rotate"
    DROP = "drop"

    # Advanced navigation
    FOLLOW = "follow"
    WALK_DIR = "walk_dir"

    # State checking
    CHECK = "check"
    FIND_ITEM = "find_item"


@dataclass
class CommandResult:
    """Result of executing a command."""
    success: bool
    message: str
    action_taken: str = ""
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


# =============================================================================
# COMMAND EXECUTOR
# =============================================================================

class AgentCommander:
    """
    Executes high-level commands from the model.

    The model issues simple text commands, and this class
    handles all the complexity of making them happen.
    """

    def __init__(
        self,
        window_bounds: Tuple[int, int, int, int],
        snapshot_fn: Callable[[], Dict[str, Any]],
    ):
        self.window_bounds = window_bounds
        self.snapshot_fn = snapshot_fn

        # Active loops
        self.skilling_loop: Optional[SkillingLoop] = None
        self.combat_loop: Optional[CombatLoop] = None
        self.bank_trip: Optional[BankTrip] = None

        # State tracking
        self.last_command: str = ""
        self.command_count: int = 0

    def execute(self, command: str, args: str = "") -> CommandResult:
        """
        Execute a command.

        Args:
            command: The command type (e.g., "talk_to", "chop", "bank")
            args: Arguments for the command (e.g., NPC name, item name)

        Returns:
            CommandResult with success status and details
        """
        self.command_count += 1
        self.last_command = f"{command} {args}".strip()

        snapshot = self.snapshot_fn()

        # Check for random events first
        random_event = detect_random_event(snapshot)
        if random_event:
            handle_random_event(random_event, self.window_bounds, self.snapshot_fn)
            return CommandResult(
                success=True,
                message=f"Handled random event: {random_event}",
                action_taken="random_event"
            )

        # Route to appropriate handler
        cmd = command.lower().strip()

        if cmd == "talk_to":
            return self._talk_to(args)
        elif cmd == "click":
            return self._click(args)
        elif cmd == "chop":
            return self._chop(args)
        elif cmd == "fish":
            return self._fish(args)
        elif cmd == "mine":
            return self._mine(args)
        elif cmd == "attack":
            return self._attack(args)
        elif cmd == "eat":
            return self._eat(args)
        elif cmd == "walk_to":
            return self._walk_to(args)
        elif cmd == "open":
            return self._open(args)
        elif cmd == "bank":
            return self._bank()
        elif cmd == "deposit":
            return self._deposit(args)
        elif cmd == "continue":
            return self._continue_dialogue()
        elif cmd == "continue_key":
            return self._continue_dialogue_key()
        elif cmd == "select":
            return self._select_option(args)
        elif cmd == "option_key":
            return self._select_option_key(args)
        elif cmd == "wait":
            return self._wait(args)
        elif cmd == "rotate":
            return self._rotate(args)
        elif cmd == "drop":
            return self._drop(args)
        elif cmd == "use":
            return self._use(args)
        elif cmd == "follow":
            return self._follow(args)
        elif cmd == "walk_dir":
            return self._walk_dir(args)
        elif cmd == "check":
            return self._check(args)
        elif cmd == "find_item":
            return self._find_item(args)
        else:
            return CommandResult(
                success=False,
                message=f"Unknown command: {command}"
            )

    # =========================================================================
    # COMMAND HANDLERS
    # =========================================================================

    def _talk_to(self, npc_name: str) -> CommandResult:
        """Talk to an NPC."""
        if not npc_name:
            return CommandResult(False, "No NPC name provided")

        result = interact_with_npc(
            npc_name,
            "Talk-to",
            self.window_bounds,
            self.snapshot_fn
        )

        return CommandResult(
            success=result.success,
            message=f"Talked to {npc_name}" if result.success else f"Could not find {npc_name}",
            action_taken="talk_to",
            details=result.details
        )

    def _click(self, target: str) -> CommandResult:
        """Click on an object or NPC."""
        if not target:
            return CommandResult(False, "No target provided")

        # Try as object first
        result = interact_with_object(
            target,
            "",  # Default action
            self.window_bounds,
            self.snapshot_fn
        )

        if result.success:
            return CommandResult(
                success=True,
                message=f"Clicked {target}",
                action_taken="click_object"
            )

        # Try as NPC
        result = interact_with_npc(
            target,
            "",
            self.window_bounds,
            self.snapshot_fn
        )

        return CommandResult(
            success=result.success,
            message=f"Clicked {target}" if result.success else f"Could not find {target}",
            action_taken="click_npc"
        )

    def _chop(self, tree_type: str = "Tree") -> CommandResult:
        """Chop a tree."""
        target = tree_type if tree_type else "Tree"

        result = interact_with_object(
            target,
            "Chop down",
            self.window_bounds,
            self.snapshot_fn
        )

        return CommandResult(
            success=result.success,
            message=f"Chopping {target}" if result.success else f"No {target} found",
            action_taken="chop"
        )

    def _fish(self, spot_type: str = "Fishing spot") -> CommandResult:
        """Fish at a fishing spot."""
        target = spot_type if spot_type else "Fishing spot"

        result = interact_with_object(
            target,
            "Fish",
            self.window_bounds,
            self.snapshot_fn
        )

        return CommandResult(
            success=result.success,
            message=f"Fishing at {target}" if result.success else f"No {target} found",
            action_taken="fish"
        )

    def _mine(self, rock_type: str = "Rocks") -> CommandResult:
        """Mine a rock."""
        target = rock_type if rock_type else "Rocks"

        result = interact_with_object(
            target,
            "Mine",
            self.window_bounds,
            self.snapshot_fn
        )

        return CommandResult(
            success=result.success,
            message=f"Mining {target}" if result.success else f"No {target} found",
            action_taken="mine"
        )

    def _attack(self, target_name: str) -> CommandResult:
        """Attack an enemy."""
        if not target_name:
            return CommandResult(False, "No target provided")

        result = interact_with_npc(
            target_name,
            "Attack",
            self.window_bounds,
            self.snapshot_fn
        )

        return CommandResult(
            success=result.success,
            message=f"Attacking {target_name}" if result.success else f"Could not find {target_name}",
            action_taken="attack"
        )

    def _eat(self, food_name: str = "") -> CommandResult:
        """Eat food from inventory."""
        snapshot = self.snapshot_fn()
        runelite = snapshot.get("runelite_data", {})
        inventory = parse_inventory_from_runelite(runelite)

        # Common food items
        food_options = [food_name] if food_name else [
            "Shrimp", "Trout", "Salmon", "Lobster", "Swordfish",
            "Bread", "Meat", "Cooked"
        ]

        for food in food_options:
            slot = find_item_in_inventory(inventory, food)
            if slot is not None:
                click_inventory_slot(slot, self.window_bounds, snapshot)
                return CommandResult(
                    success=True,
                    message=f"Eating {food}",
                    action_taken="eat",
                    details={"food": food, "slot": slot}
                )

        return CommandResult(
            success=False,
            message="No food found in inventory"
        )

    def _walk_to(self, target: str) -> CommandResult:
        """Walk to a target."""
        if not target:
            return CommandResult(False, "No target provided")

        result = search_and_click(
            target,
            self.window_bounds,
            self.snapshot_fn
        )

        return CommandResult(
            success=result.success,
            message=f"Walking to {target}" if result.success else f"Could not find {target}",
            action_taken="walk_to"
        )

    def _open(self, target: str) -> CommandResult:
        """Open a door, gate, or other openable object."""
        if not target:
            return CommandResult(False, "No target provided")

        result = interact_with_object(
            target,
            "Open",
            self.window_bounds,
            self.snapshot_fn
        )

        return CommandResult(
            success=result.success,
            message=f"Opening {target}" if result.success else f"Could not find {target}",
            action_taken="open"
        )

    def _bank(self) -> CommandResult:
        """Open a bank."""
        if open_bank(self.window_bounds, self.snapshot_fn):
            return CommandResult(
                success=True,
                message="Bank opened",
                action_taken="bank"
            )
        return CommandResult(
            success=False,
            message="Could not find bank"
        )

    def _deposit(self, item: str = "all") -> CommandResult:
        """Deposit items in bank."""
        snapshot = self.snapshot_fn()

        if not detect_bank_open(snapshot):
            return CommandResult(False, "Bank not open")

        if item.lower() == "all" or not item:
            deposit_all(self.window_bounds, snapshot)
            return CommandResult(
                success=True,
                message="Deposited all items",
                action_taken="deposit_all"
            )

        return CommandResult(
            success=False,
            message="Specific item deposit not implemented"
        )

    def _continue_dialogue(self) -> CommandResult:
        """Continue through dialogue."""
        snapshot = self.snapshot_fn()
        dialogue = detect_dialogue_state(snapshot)

        if dialogue.state == DialogueState.NONE:
            return CommandResult(False, "No dialogue active")

        if dialogue.continue_available or dialogue.state == DialogueState.NPC_CHAT:
            click_dialogue_continue(snapshot, self.window_bounds)
            return CommandResult(
                success=True,
                message="Continued dialogue",
                action_taken="continue"
            )

        return CommandResult(False, "No continue option available")

    def _continue_dialogue_key(self) -> CommandResult:
        """Continue through dialogue using spacebar (faster, more reliable)."""
        snapshot = self.snapshot_fn()
        dialogue = detect_dialogue_state(snapshot)

        if dialogue.state == DialogueState.NONE:
            return CommandResult(False, "No dialogue active")

        # Log dialogue before continuing
        chat_logger = get_chat_logger()
        chat_logger.log_dialogue(dialogue)

        result = press_dialogue_continue()
        return CommandResult(
            success=result.success,
            message="Pressed SPACE to continue",
            action_taken="continue_key"
        )

    def _select_option_key(self, option: str) -> CommandResult:
        """Select dialogue option using number key (1-5)."""
        snapshot = self.snapshot_fn()
        dialogue = detect_dialogue_state(snapshot)

        if dialogue.state != DialogueState.PLAYER_OPTIONS:
            return CommandResult(False, "No dialogue options available")

        # Log dialogue before selecting
        chat_logger = get_chat_logger()
        chat_logger.log_dialogue(dialogue)

        # Parse option number
        try:
            opt_num = int(option.strip()) if option else 1
        except ValueError:
            opt_num = 1

        result = press_dialogue_option(opt_num)
        return CommandResult(
            success=result.success,
            message=f"Pressed {opt_num} to select option",
            action_taken="option_key"
        )

    def _select_option(self, option_text: str) -> CommandResult:
        """Select a dialogue option."""
        snapshot = self.snapshot_fn()

        result = select_dialogue_by_text(
            option_text,
            snapshot,
            self.window_bounds
        )

        return CommandResult(
            success=result.success,
            message=f"Selected '{option_text}'" if result.success else f"Option not found",
            action_taken="select"
        )

    def _wait(self, duration: str = "1") -> CommandResult:
        """Wait for a duration (in game ticks)."""
        try:
            ticks = int(duration) if duration else 1
        except ValueError:
            ticks = 1

        # 1 tick = 600ms
        time.sleep(ticks * 0.6)

        return CommandResult(
            success=True,
            message=f"Waited {ticks} ticks",
            action_taken="wait"
        )

    def _rotate(self, direction: str = "right") -> CommandResult:
        """Rotate camera."""
        direction = direction.lower() if direction else "right"
        if direction not in ("left", "right", "up", "down"):
            direction = "right"

        rotate_camera(direction, amount=2)

        return CommandResult(
            success=True,
            message=f"Rotated camera {direction}",
            action_taken="rotate"
        )

    def _drop(self, item: str) -> CommandResult:
        """Drop an item from inventory."""
        snapshot = self.snapshot_fn()
        runelite = snapshot.get("runelite_data", {})
        inventory = parse_inventory_from_runelite(runelite)

        if item:
            slot = find_item_in_inventory(inventory, item)
            if slot is not None:
                drop_item(slot, self.window_bounds, snapshot)
                return CommandResult(
                    success=True,
                    message=f"Dropped {item}",
                    action_taken="drop"
                )
            return CommandResult(False, f"Item '{item}' not found")

        return CommandResult(False, "No item specified")

    def _use(self, args: str) -> CommandResult:
        """Use item on something. Format: 'item on target'"""
        if " on " not in args.lower():
            return CommandResult(False, "Format: 'item on target'")

        parts = args.lower().split(" on ")
        item_name = parts[0].strip()
        target_name = parts[1].strip()

        snapshot = self.snapshot_fn()
        runelite = snapshot.get("runelite_data", {})
        inventory = parse_inventory_from_runelite(runelite)

        slot = find_item_in_inventory(inventory, item_name)
        if slot is None:
            return CommandResult(False, f"Item '{item_name}' not found")

        # Click item
        click_inventory_slot(slot, self.window_bounds, snapshot)
        time.sleep(random.uniform(0.2, 0.4))

        # Click target
        result = search_and_click(target_name, self.window_bounds, self.snapshot_fn)

        return CommandResult(
            success=result.success,
            message=f"Used {item_name} on {target_name}" if result.success else f"Could not find {target_name}",
            action_taken="use"
        )

    def _follow(self, npc_name: str) -> CommandResult:
        """Follow a moving NPC until close enough to interact."""
        if not npc_name:
            return CommandResult(False, "No NPC name provided")

        result = follow_npc(
            npc_name,
            self.window_bounds,
            self.snapshot_fn
        )

        return CommandResult(
            success=result.success,
            message=f"Following {npc_name}" if result.success else f"Lost sight of {npc_name}",
            action_taken="follow",
            details=result.details
        )

    def _walk_dir(self, args: str) -> CommandResult:
        """Walk in a compass direction. Format: 'north medium' or 'sw far'"""
        parts = args.lower().split()
        direction = parts[0] if parts else "north"
        distance = parts[1] if len(parts) > 1 else "medium"

        result = walk_direction(
            direction,
            distance,
            self.window_bounds,
            self.snapshot_fn
        )

        return CommandResult(
            success=result.success,
            message=f"Walking {direction} ({distance})",
            action_taken="walk_dir",
            details={"direction": direction, "distance": distance}
        )

    def _check(self, target: str) -> CommandResult:
        """Check the state of an object (depleted tree, empty rock, etc.)"""
        if not target:
            return CommandResult(False, "No target provided")

        # Determine expected actions based on common object types
        expected = []
        target_lower = target.lower()
        if "tree" in target_lower:
            expected = ["Chop"]
        elif "rock" in target_lower or "ore" in target_lower:
            expected = ["Mine"]
        elif "spot" in target_lower or "fish" in target_lower:
            expected = ["Fish", "Net", "Cage", "Harpoon"]

        state = detect_object_state(
            target,
            self.window_bounds,
            self.snapshot_fn,
            expected_actions=expected if expected else None
        )

        if not state.exists:
            return CommandResult(
                success=True,
                message=f"{target} not found",
                action_taken="check",
                details={"exists": False, "depleted": True}
            )

        return CommandResult(
            success=True,
            message=f"{target} is {'depleted' if state.is_depleted else 'available'}",
            action_taken="check",
            details={
                "exists": state.exists,
                "depleted": state.is_depleted,
                "interactable": state.is_interactable
            }
        )

    def _find_item(self, item_name: str) -> CommandResult:
        """Find an item in inventory by scanning with hover text."""
        if not item_name:
            return CommandResult(False, "No item name provided")

        slot = find_item_slot_by_hover(
            item_name,
            self.window_bounds,
            self.snapshot_fn
        )

        if slot is not None:
            return CommandResult(
                success=True,
                message=f"Found {item_name} in slot {slot}",
                action_taken="find_item",
                details={"item": item_name, "slot": slot}
            )

        return CommandResult(
            success=False,
            message=f"{item_name} not found in inventory",
            action_taken="find_item"
        )


# =============================================================================
# SIMPLE TEXT PARSER
# =============================================================================

def parse_model_command(text: str) -> Tuple[str, str]:
    """
    Parse a command from model output.

    Handles formats like:
    - "talk_to Survival Expert"
    - "chop Oak tree"
    - "BANK"
    - "wait 3"
    - "use tinderbox on logs"

    Returns (command, args)
    """
    text = text.strip()
    if not text:
        return "", ""

    # Split into command and args
    parts = text.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    return command, args


def get_available_commands() -> List[str]:
    """Get list of available commands for the model."""
    return [
        # Interaction
        "talk_to <npc_name>",
        "click <target>",
        "use <item> on <target>",

        # Skilling
        "chop [tree_type]",
        "fish [spot_type]",
        "mine [rock_type]",

        # Combat
        "attack <enemy_name>",
        "eat [food_name]",

        # Navigation
        "walk_to <target>",
        "walk_dir <direction> [distance]",  # e.g., "walk_dir north far"
        "follow <npc_name>",
        "open <door/gate>",
        "rotate [left|right|up|down]",

        # Banking
        "bank",
        "deposit [all|item_name]",

        # Dialogue (keyboard - preferred)
        "continue_key",  # Press spacebar
        "option_key <1-5>",  # Press number key
        # Dialogue (mouse - legacy)
        "continue",
        "select <option_text>",

        # State checking
        "check <object>",      # Check if tree/rock is depleted
        "find_item <name>",    # Find item in inventory

        # Utility
        "wait [ticks]",
        "drop <item_name>",
    ]


def get_context_for_model(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build context dict for the model's decision making.

    Returns a simplified view of the game state that the model can use.
    """
    context = {
        "hover_text": get_hover_text(snapshot),
        "dialogue_active": False,
        "dialogue_options": [],
        "inventory_full": is_inventory_full(snapshot),
        "health_percent": get_health_percent(snapshot),
        "in_combat": False,
        "random_event": None,
        "location": "unknown",
    }

    # Dialogue state
    dialogue = detect_dialogue_state(snapshot)
    if dialogue.state != DialogueState.NONE:
        context["dialogue_active"] = True
        context["dialogue_options"] = dialogue.options
        context["dialogue_text"] = dialogue.text

    # Combat state
    cues = snapshot.get("cues", {})
    if cues.get("animation_state") in ("attacking", "combat"):
        context["in_combat"] = True

    # Random event
    event = detect_random_event(snapshot)
    if event:
        context["random_event"] = event

    # Location from derived state
    derived = snapshot.get("derived", {})
    location = derived.get("location", {})
    context["location"] = location.get("region", "unknown")

    return context
