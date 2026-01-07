"""
Autonomy Features - Self-sufficient agent behaviors.

Provides:
- Inventory intelligence (tracking, finding items, full detection)
- Skilling loops (generic framework + specific skills)
- Banking (open, deposit, withdraw, close)
- Combat (targeting, eating, looting)
- Random event handling
- World awareness
"""
from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.game_actions import (
    get_hover_text,
    hover_text_contains,
    click_inventory_slot,
    get_inventory_slot_position,
    find_object_by_hover,
    interact_with_object,
    interact_with_npc,
    click_minimap,
    rotate_camera,
    detect_dialogue_state,
    DialogueState,
    click_dialogue_continue,
)
from src.input_exec import move_mouse_path, click, get_cursor_pos


# =============================================================================
# INVENTORY INTELLIGENCE
# =============================================================================

@dataclass
class InventorySlot:
    """Information about an inventory slot."""
    slot_id: int
    item_name: str = ""
    item_id: int = 0
    quantity: int = 0
    is_empty: bool = True


@dataclass
class InventoryState:
    """Full inventory state."""
    slots: List[InventorySlot] = field(default_factory=list)
    free_slots: int = 28
    is_full: bool = False

    def __post_init__(self):
        if not self.slots:
            self.slots = [InventorySlot(slot_id=i) for i in range(28)]


def parse_inventory_from_runelite(runelite_data: Dict[str, Any]) -> InventoryState:
    """
    Parse inventory state from RuneLite plugin data.
    RuneLite exports inventory to session_stats.json.
    """
    state = InventoryState()

    inventory_data = runelite_data.get("inventory", [])
    if not inventory_data:
        return state

    filled = 0
    for item in inventory_data:
        slot_id = item.get("slot", -1)
        if 0 <= slot_id < 28:
            state.slots[slot_id] = InventorySlot(
                slot_id=slot_id,
                item_name=item.get("name", ""),
                item_id=item.get("id", 0),
                quantity=item.get("quantity", 1),
                is_empty=False
            )
            filled += 1

    state.free_slots = 28 - filled
    state.is_full = filled >= 28

    return state


def find_item_in_inventory(
    inventory: InventoryState,
    item_name: str,
) -> Optional[int]:
    """
    Find an item in inventory by name.
    Returns slot index (0-27) or None if not found.
    """
    name_lower = item_name.lower()
    for slot in inventory.slots:
        if not slot.is_empty and name_lower in slot.item_name.lower():
            return slot.slot_id
    return None


def find_empty_slot(inventory: InventoryState) -> Optional[int]:
    """Find first empty inventory slot."""
    for slot in inventory.slots:
        if slot.is_empty:
            return slot.slot_id
    return None


def count_item(inventory: InventoryState, item_name: str) -> int:
    """Count total quantity of an item in inventory."""
    name_lower = item_name.lower()
    total = 0
    for slot in inventory.slots:
        if not slot.is_empty and name_lower in slot.item_name.lower():
            total += slot.quantity
    return total


def is_inventory_full(snapshot: Dict[str, Any]) -> bool:
    """
    Check if inventory is full from snapshot.
    Uses multiple detection methods.
    """
    # Method 1: Check RuneLite data
    runelite = snapshot.get("runelite_data", {})
    if runelite:
        inv = parse_inventory_from_runelite(runelite)
        if inv.is_full:
            return True

    # Method 2: Check for "inventory full" message in chat
    chat = snapshot.get("chat", [])
    for line in chat:
        if isinstance(line, str) and "inventory" in line.lower() and "full" in line.lower():
            return True

    # Method 3: Check OCR for inventory region
    for ocr_item in snapshot.get("ocr", []):
        if isinstance(ocr_item, dict) and ocr_item.get("region") == "inventory":
            # If we can read 28 distinct items, inventory is full
            pass  # Complex detection, skip for now

    return False


def use_item_on_object(
    item_slot: int,
    object_text: str,
    window_bounds: Tuple[int, int, int, int],
    snapshot: Dict[str, Any],
    snapshot_fn: Callable[[], Dict[str, Any]],
) -> bool:
    """
    Use an inventory item on a world object.
    1. Click item in inventory
    2. Find and click the object
    """
    # Click the item first
    result = click_inventory_slot(item_slot, window_bounds, snapshot)
    if not result.success:
        return False

    time.sleep(random.uniform(0.2, 0.4))

    # Find and click the object
    pos = find_object_by_hover(object_text, window_bounds, snapshot_fn)
    if not pos:
        return False

    x, y = pos
    click(button='left', dwell_ms=random.randint(45, 80))
    return True


# =============================================================================
# SKILLING LOOPS
# =============================================================================

class SkillingState(Enum):
    """State of a skilling activity."""
    IDLE = "idle"
    SEARCHING = "searching"
    INTERACTING = "interacting"
    WAITING = "waiting"
    BANKING = "banking"
    DROPPING = "dropping"


@dataclass
class SkillingConfig:
    """Configuration for a skilling loop."""
    skill_name: str
    resource_names: List[str]  # e.g., ["Oak tree", "Tree"]
    action: str  # e.g., "Chop down"
    product_name: str  # e.g., "Oak logs"
    bank_when_full: bool = True
    drop_when_full: bool = False
    bank_location: Optional[Tuple[int, int]] = None  # Minimap offset to bank


@dataclass
class SkillingLoop:
    """
    Generic skilling loop controller.

    Handles: find resource → interact → wait → check inventory → repeat/bank
    """
    config: SkillingConfig
    state: SkillingState = SkillingState.IDLE
    ticks_waiting: int = 0
    last_resource_pos: Optional[Tuple[int, int]] = None
    items_collected: int = 0

    def tick(
        self,
        snapshot: Dict[str, Any],
        window_bounds: Tuple[int, int, int, int],
        snapshot_fn: Callable[[], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Execute one tick of the skilling loop.
        Returns status dict.
        """
        result = {"state": self.state.value, "action": None}

        # Check if inventory is full
        if is_inventory_full(snapshot):
            if self.config.drop_when_full:
                self.state = SkillingState.DROPPING
            elif self.config.bank_when_full:
                self.state = SkillingState.BANKING
            else:
                result["action"] = "inventory_full_stopped"
                return result

        if self.state == SkillingState.IDLE:
            self.state = SkillingState.SEARCHING
            result["action"] = "starting_search"

        elif self.state == SkillingState.SEARCHING:
            # Try to find a resource
            for resource_name in self.config.resource_names:
                pos = find_object_by_hover(
                    resource_name,
                    window_bounds,
                    snapshot_fn,
                    max_positions=25
                )
                if pos:
                    self.last_resource_pos = pos
                    # Click to interact
                    click(button='left', dwell_ms=random.randint(45, 80))
                    self.state = SkillingState.INTERACTING
                    result["action"] = f"found_{resource_name}"
                    return result

            # No resource found, try rotating camera
            rotate_camera('right', amount=2)
            result["action"] = "rotating_to_find_resource"

        elif self.state == SkillingState.INTERACTING:
            # Check if we're still interacting (animation state)
            cues = snapshot.get("cues", {})
            animation = cues.get("animation_state", "unknown")

            if animation in ("idle", "unknown"):
                self.ticks_waiting += 1
                if self.ticks_waiting > 5:
                    # Probably done with this resource
                    self.state = SkillingState.SEARCHING
                    self.ticks_waiting = 0
                    self.items_collected += 1
                    result["action"] = "resource_depleted"
            else:
                self.ticks_waiting = 0
                result["action"] = "still_skilling"

        elif self.state == SkillingState.WAITING:
            self.ticks_waiting += 1
            if self.ticks_waiting > 10:
                self.state = SkillingState.SEARCHING
                self.ticks_waiting = 0

        elif self.state == SkillingState.DROPPING:
            result["action"] = "dropping_items"
            # Drop logic handled externally
            self.state = SkillingState.IDLE

        elif self.state == SkillingState.BANKING:
            result["action"] = "need_to_bank"
            # Banking handled externally

        result["state"] = self.state.value
        result["items_collected"] = self.items_collected
        return result


# Predefined skilling configs
WOODCUTTING_CONFIG = SkillingConfig(
    skill_name="Woodcutting",
    resource_names=["Tree", "Oak tree", "Willow tree", "Maple tree", "Yew tree"],
    action="Chop down",
    product_name="logs",
    bank_when_full=True,
)

FISHING_CONFIG = SkillingConfig(
    skill_name="Fishing",
    resource_names=["Fishing spot", "Rod Fishing spot", "Net Fishing spot"],
    action="Fish",
    product_name="fish",
    bank_when_full=True,
)

MINING_CONFIG = SkillingConfig(
    skill_name="Mining",
    resource_names=["Rocks", "Copper rocks", "Tin rocks", "Iron rocks"],
    action="Mine",
    product_name="ore",
    bank_when_full=True,
)


# =============================================================================
# BANKING
# =============================================================================

class BankState(Enum):
    """Banking state."""
    CLOSED = "closed"
    OPENING = "opening"
    OPEN = "open"
    DEPOSITING = "depositing"
    WITHDRAWING = "withdrawing"


def detect_bank_open(snapshot: Dict[str, Any]) -> bool:
    """Check if bank interface is open."""
    ui = snapshot.get("ui", {})
    open_interface = ui.get("open_interface", "none")

    if open_interface in ("bank", "bank_interface"):
        return True

    # Check OCR for bank-specific text
    for ocr_item in snapshot.get("ocr", []):
        if isinstance(ocr_item, dict):
            text = ocr_item.get("text", "").lower()
            if "deposit" in text and "withdraw" in text:
                return True
            if "bank of" in text:
                return True

    return False


def open_bank(
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
) -> bool:
    """
    Attempt to open a bank.
    Looks for bank booth or banker NPC.
    """
    # Try bank booth first
    result = interact_with_object(
        "Bank booth",
        "Bank",
        window_bounds,
        snapshot_fn
    )
    if result.success:
        time.sleep(random.uniform(0.8, 1.2))
        return True

    # Try banker NPC
    result = interact_with_npc(
        "Banker",
        "Bank",
        window_bounds,
        snapshot_fn
    )
    if result.success:
        time.sleep(random.uniform(0.8, 1.2))
        return True

    return False


def deposit_all(
    window_bounds: Tuple[int, int, int, int],
    snapshot: Dict[str, Any],
) -> bool:
    """
    Click the 'Deposit inventory' button in bank interface.
    Button is typically near bottom of bank interface.
    """
    win_x, win_y, win_w, win_h = window_bounds

    # Deposit inventory button location (approximate)
    # Usually bottom-left area of bank interface
    deposit_x = win_x + 450 + random.randint(-5, 5)
    deposit_y = win_y + 320 + random.randint(-3, 3)

    move_mouse_path(deposit_x, deposit_y, steps=10, curve_strength=0.12)
    time.sleep(random.uniform(0.05, 0.1))
    click(button='left', dwell_ms=random.randint(40, 70))

    return True


def close_bank(
    window_bounds: Tuple[int, int, int, int],
) -> bool:
    """Close bank interface by pressing Escape."""
    from src.input_exec import press_key_name
    press_key_name('ESCAPE', hold_ms=random.randint(40, 80))
    return True


@dataclass
class BankTrip:
    """
    Manages a complete bank trip.
    Walk to bank → open → deposit → close → walk back
    """
    bank_minimap_offset: Tuple[int, int]
    return_minimap_offset: Tuple[int, int]
    state: BankState = BankState.CLOSED

    def tick(
        self,
        snapshot: Dict[str, Any],
        window_bounds: Tuple[int, int, int, int],
        snapshot_fn: Callable[[], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute one tick of bank trip."""
        result = {"state": self.state.value, "action": None}

        if self.state == BankState.CLOSED:
            # Walk to bank
            click_minimap(
                self.bank_minimap_offset[0],
                self.bank_minimap_offset[1],
                window_bounds,
                snapshot
            )
            self.state = BankState.OPENING
            result["action"] = "walking_to_bank"

        elif self.state == BankState.OPENING:
            # Check if at bank, try to open
            if open_bank(window_bounds, snapshot_fn):
                self.state = BankState.OPEN
                result["action"] = "bank_opened"
            else:
                result["action"] = "waiting_to_reach_bank"

        elif self.state == BankState.OPEN:
            if detect_bank_open(snapshot):
                deposit_all(window_bounds, snapshot)
                self.state = BankState.DEPOSITING
                result["action"] = "depositing"
            else:
                self.state = BankState.OPENING

        elif self.state == BankState.DEPOSITING:
            # Close bank and return
            close_bank(window_bounds)
            time.sleep(random.uniform(0.3, 0.5))

            # Walk back
            click_minimap(
                self.return_minimap_offset[0],
                self.return_minimap_offset[1],
                window_bounds,
                snapshot
            )
            self.state = BankState.CLOSED
            result["action"] = "returning_to_activity"

        return result


# =============================================================================
# COMBAT
# =============================================================================

class CombatState(Enum):
    """Combat state."""
    IDLE = "idle"
    TARGETING = "targeting"
    IN_COMBAT = "in_combat"
    EATING = "eating"
    LOOTING = "looting"
    FLEEING = "fleeing"


@dataclass
class CombatConfig:
    """Combat configuration."""
    target_names: List[str]  # NPCs to attack
    eat_at_hp_percent: float = 50.0
    flee_at_hp_percent: float = 20.0
    food_names: List[str] = field(default_factory=lambda: ["Shrimp", "Trout", "Lobster"])
    loot_items: List[str] = field(default_factory=list)  # Items to pick up


def detect_in_combat(snapshot: Dict[str, Any]) -> bool:
    """Check if player is in combat."""
    cues = snapshot.get("cues", {})

    # Check animation state
    animation = cues.get("animation_state", "")
    if animation in ("attacking", "combat"):
        return True

    # Check for combat-related hover text
    ui = snapshot.get("ui", {})
    hover = ui.get("hover_text", "")
    if "attack" in hover.lower():
        return True

    return False


def get_health_percent(snapshot: Dict[str, Any]) -> float:
    """Get current health percentage from snapshot."""
    # Try RuneLite data first
    runelite = snapshot.get("runelite_data", {})
    if runelite:
        current = runelite.get("current_hp", 0)
        max_hp = runelite.get("max_hp", 1)
        if max_hp > 0:
            return (current / max_hp) * 100

    # Fallback: try to parse from skills
    account = snapshot.get("account", {})
    skills = account.get("skills", {})
    hitpoints = skills.get("hitpoints", {})
    if hitpoints:
        current = hitpoints.get("current", hitpoints.get("level", 10))
        max_hp = hitpoints.get("level", 10)
        if max_hp > 0:
            return (current / max_hp) * 100

    return 100.0  # Assume full health if unknown


@dataclass
class CombatLoop:
    """
    Combat loop controller.
    Handles: target → attack → eat if needed → loot → repeat
    """
    config: CombatConfig
    state: CombatState = CombatState.IDLE
    kills: int = 0
    current_target: Optional[str] = None

    def tick(
        self,
        snapshot: Dict[str, Any],
        window_bounds: Tuple[int, int, int, int],
        snapshot_fn: Callable[[], Dict[str, Any]],
        inventory: Optional[InventoryState] = None,
    ) -> Dict[str, Any]:
        """Execute one tick of combat loop."""
        result = {"state": self.state.value, "action": None}

        hp_percent = get_health_percent(snapshot)

        # Priority: flee if critical
        if hp_percent <= self.config.flee_at_hp_percent:
            self.state = CombatState.FLEEING
            result["action"] = "fleeing_low_hp"
            # Run away - click far on minimap
            click_minimap(random.randint(-50, 50), random.randint(-50, 50), window_bounds, snapshot)
            return result

        # Priority: eat if low HP
        if hp_percent <= self.config.eat_at_hp_percent:
            if inventory:
                for food_name in self.config.food_names:
                    slot = find_item_in_inventory(inventory, food_name)
                    if slot is not None:
                        click_inventory_slot(slot, window_bounds, snapshot)
                        self.state = CombatState.EATING
                        result["action"] = f"eating_{food_name}"
                        return result

        if self.state == CombatState.IDLE:
            self.state = CombatState.TARGETING

        elif self.state == CombatState.TARGETING:
            # Find and attack target
            for target_name in self.config.target_names:
                target_result = interact_with_npc(
                    target_name,
                    "Attack",
                    window_bounds,
                    snapshot_fn
                )
                if target_result.success:
                    self.current_target = target_name
                    self.state = CombatState.IN_COMBAT
                    result["action"] = f"attacking_{target_name}"
                    return result

            # No target found, rotate camera
            rotate_camera('right', amount=2)
            result["action"] = "searching_for_target"

        elif self.state == CombatState.IN_COMBAT:
            if detect_in_combat(snapshot):
                result["action"] = "fighting"
            else:
                # Combat ended - either killed or target ran
                self.kills += 1
                if self.config.loot_items:
                    self.state = CombatState.LOOTING
                else:
                    self.state = CombatState.TARGETING
                result["action"] = "combat_ended"

        elif self.state == CombatState.LOOTING:
            # Try to pick up loot
            for item_name in self.config.loot_items:
                pos = find_object_by_hover(item_name, window_bounds, snapshot_fn, max_positions=10)
                if pos:
                    click(button='left', dwell_ms=random.randint(40, 70))
                    result["action"] = f"looting_{item_name}"
                    return result

            # No more loot, back to targeting
            self.state = CombatState.TARGETING
            result["action"] = "done_looting"

        elif self.state == CombatState.EATING:
            # Brief pause after eating
            time.sleep(random.uniform(0.3, 0.6))
            self.state = CombatState.IN_COMBAT if detect_in_combat(snapshot) else CombatState.TARGETING

        result["kills"] = self.kills
        return result


# =============================================================================
# RANDOM EVENTS
# =============================================================================

RANDOM_EVENT_NPCS = [
    "Genie",
    "Dr Jekyll",
    "Drunken Dwarf",
    "Surprise Exam",
    "Evil Chicken",
    "Swarm",
    "Bee Keeper",
    "Capt' Arnav",
    "Niles",
    "Miles",
    "Giles",
    "Frog",
    "Rick Turpentine",
    "Sandwich lady",
    "Strange plant",
    "Quiz Master",
    "Sergeant Damien",
    "Freaky Forester",
    "Leo the Gravedigger",
    "Mysterious Old Man",
    "Pillory Guard",
    "Prison Pete",
    "Count Check",
    "Flippa",
]


def detect_random_event(snapshot: Dict[str, Any]) -> Optional[str]:
    """
    Detect if a random event NPC is present.
    Returns NPC name if found, None otherwise.
    """
    # Check RuneLite data for nearby NPCs
    runelite = snapshot.get("runelite_data", {})
    nearby_npcs = runelite.get("nearby_npcs", [])

    for npc in nearby_npcs:
        npc_name = npc.get("name", "")
        for event_npc in RANDOM_EVENT_NPCS:
            if event_npc.lower() in npc_name.lower():
                return event_npc

    # Check chat for random event messages
    chat = snapshot.get("chat", [])
    for line in chat:
        if isinstance(line, str):
            line_lower = line.lower()
            for event_npc in RANDOM_EVENT_NPCS:
                if event_npc.lower() in line_lower:
                    return event_npc

    return None


def handle_random_event(
    event_name: str,
    window_bounds: Tuple[int, int, int, int],
    snapshot_fn: Callable[[], Dict[str, Any]],
) -> bool:
    """
    Handle a random event.
    Returns True if handled, False if unknown event.
    """
    event_lower = event_name.lower()

    # Genie - just talk for lamp
    if "genie" in event_lower:
        result = interact_with_npc("Genie", "Talk-to", window_bounds, snapshot_fn)
        return result.success

    # Dismiss events - just click to dismiss
    dismissable = ["drunken dwarf", "sandwich lady", "dr jekyll", "mysterious old man"]
    for dismiss in dismissable:
        if dismiss in event_lower:
            result = interact_with_npc(event_name, "Dismiss", window_bounds, snapshot_fn)
            if not result.success:
                # Try talk-to as fallback
                result = interact_with_npc(event_name, "Talk-to", window_bounds, snapshot_fn)
            return result.success

    # For complex events, just try to dismiss/talk
    result = interact_with_npc(event_name, "Dismiss", window_bounds, snapshot_fn)
    return result.success


# =============================================================================
# WORLD AWARENESS
# =============================================================================

@dataclass
class WorldState:
    """Current world/game state."""
    player_x: int = 0
    player_y: int = 0
    player_plane: int = 0
    region_id: int = 0
    is_logged_in: bool = True
    is_in_combat: bool = False
    nearby_players: int = 0
    nearby_npcs: List[str] = field(default_factory=list)


def parse_world_state(snapshot: Dict[str, Any]) -> WorldState:
    """Parse world state from snapshot and RuneLite data."""
    state = WorldState()

    runelite = snapshot.get("runelite_data", {})
    if runelite:
        player = runelite.get("player", {})
        state.player_x = player.get("x", 0)
        state.player_y = player.get("y", 0)
        state.player_plane = player.get("plane", 0)
        state.region_id = runelite.get("region_id", 0)

        nearby = runelite.get("nearby_npcs", [])
        state.nearby_npcs = [n.get("name", "") for n in nearby if n.get("name")]

        players = runelite.get("nearby_players", [])
        state.nearby_players = len(players)

    state.is_in_combat = detect_in_combat(snapshot)

    # Check for login state
    ui = snapshot.get("ui", {})
    if ui.get("open_interface") == "login":
        state.is_logged_in = False

    return state


def detect_death(snapshot: Dict[str, Any]) -> bool:
    """Check if player has died."""
    # Check for death screen
    ui = snapshot.get("ui", {})
    if ui.get("open_interface") in ("death", "respawn"):
        return True

    # Check chat for death message
    chat = snapshot.get("chat", [])
    for line in chat:
        if isinstance(line, str) and "oh dear" in line.lower() and "dead" in line.lower():
            return True

    return False


def is_player_idle(snapshot: Dict[str, Any], idle_ticks: int = 3) -> bool:
    """Check if player has been idle for N ticks."""
    cues = snapshot.get("cues", {})
    animation = cues.get("animation_state", "unknown")

    return animation in ("idle", "unknown", "")


# =============================================================================
# ACTIVITY SCHEDULER
# =============================================================================

@dataclass
class ScheduledActivity:
    """An activity scheduled for execution."""
    name: str
    duration_minutes: float
    skill: Optional[str] = None
    config: Optional[Any] = None
    priority: int = 0


class ActivityScheduler:
    """
    Manages activity scheduling and breaks.
    """

    def __init__(self):
        self.activities: List[ScheduledActivity] = []
        self.current_activity: Optional[ScheduledActivity] = None
        self.activity_start_time: float = 0
        self.total_session_time: float = 0
        self.break_interval_minutes: float = 45.0
        self.break_duration_minutes: float = 5.0
        self.last_break_time: float = 0

    def add_activity(self, activity: ScheduledActivity) -> None:
        """Add an activity to the schedule."""
        self.activities.append(activity)
        self.activities.sort(key=lambda a: -a.priority)

    def start_next_activity(self) -> Optional[ScheduledActivity]:
        """Start the next scheduled activity."""
        if not self.activities:
            return None

        self.current_activity = self.activities.pop(0)
        self.activity_start_time = time.time()
        return self.current_activity

    def should_take_break(self) -> bool:
        """Check if it's time for a break."""
        now = time.time()
        time_since_break = (now - self.last_break_time) / 60.0

        return time_since_break >= self.break_interval_minutes

    def take_break(self) -> float:
        """
        Take a break.
        Returns duration in seconds.
        """
        duration = self.break_duration_minutes * 60
        # Add some randomness
        duration *= random.uniform(0.8, 1.2)

        self.last_break_time = time.time()
        return duration

    def is_activity_complete(self) -> bool:
        """Check if current activity duration has elapsed."""
        if not self.current_activity:
            return True

        elapsed = (time.time() - self.activity_start_time) / 60.0
        return elapsed >= self.current_activity.duration_minutes

    def get_session_time_minutes(self) -> float:
        """Get total session time in minutes."""
        return self.total_session_time / 60.0
