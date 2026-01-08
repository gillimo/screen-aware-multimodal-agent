"""
Autonomy Features Module

This module implements:
- T6: Obstacle detection and avoidance
- T7: Long-distance navigation with landmarks
- T9: Smart item organization
- T10: Goal-based activity selection
- T11: Daily task rotation
- T12: Prayer flicking support
- T13: Quiz master random event handler
- T14: Frog princess random event handler
- T15: Safe-spot detection
- T16: Resource availability scanning

Nightfall - 2026-01-07
"""
from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# T6: OBSTACLE DETECTION AND AVOIDANCE
# =============================================================================

class ObstacleType(Enum):
    """Types of obstacles that can block movement."""
    WALL = "wall"
    WATER = "water"
    FENCE = "fence"
    DOOR_CLOSED = "door_closed"
    GATE_CLOSED = "gate_closed"
    NPC_BLOCKING = "npc_blocking"
    PLAYER_BLOCKING = "player_blocking"
    OBJECT = "object"
    UNKNOWN = "unknown"


@dataclass
class Obstacle:
    """Represents a detected obstacle."""
    obstacle_type: ObstacleType
    position: Tuple[int, int]  # Screen coordinates
    world_position: Optional[Tuple[int, int, int]] = None
    can_bypass: bool = False
    bypass_action: str = ""  # e.g., "open", "climb", "jump"


class ObstacleDetector:
    """
    Detects obstacles in the player's path (T6).

    Uses hover text analysis and position history to detect when
    the player is blocked by an obstacle.
    """

    # Keywords indicating obstacles in hover text
    OBSTACLE_KEYWORDS = {
        ObstacleType.WALL: ["wall", "stone wall", "brick wall"],
        ObstacleType.WATER: ["water", "river", "lake", "sea", "pond"],
        ObstacleType.FENCE: ["fence", "railing", "barrier"],
        ObstacleType.DOOR_CLOSED: ["door", "closed door"],
        ObstacleType.GATE_CLOSED: ["gate", "closed gate"],
    }

    # Actions that can bypass obstacles
    BYPASS_ACTIONS = {
        ObstacleType.DOOR_CLOSED: ["open", "push"],
        ObstacleType.GATE_CLOSED: ["open"],
        ObstacleType.FENCE: ["climb", "jump-over"],
    }

    def __init__(self):
        self.position_history: List[Tuple[int, int, int, float]] = []
        self.last_successful_move: float = 0.0

    def detect_obstacle(
        self,
        snapshot: Dict[str, Any],
        target_direction: Tuple[int, int],
    ) -> Optional[Obstacle]:
        """
        Detect if there's an obstacle in the target direction.

        Args:
            snapshot: Current game snapshot
            target_direction: Direction we're trying to move (dx, dy)

        Returns:
            Obstacle if detected, None otherwise
        """
        # Check hover text for obstacle indicators
        ui = snapshot.get("ui", {})
        hover_text = ui.get("hover_text", "").lower()

        for obs_type, keywords in self.OBSTACLE_KEYWORDS.items():
            if any(kw in hover_text for kw in keywords):
                # Determine if it can be bypassed
                bypass_actions = self.BYPASS_ACTIONS.get(obs_type, [])
                can_bypass = any(action in hover_text for action in bypass_actions)
                bypass_action = next((a for a in bypass_actions if a in hover_text), "")

                return Obstacle(
                    obstacle_type=obs_type,
                    position=(0, 0),  # Would need screen coords from detection
                    can_bypass=can_bypass,
                    bypass_action=bypass_action,
                )

        # Check if we're stuck (position not changing)
        runelite = snapshot.get("runelite_data", {})
        pos = runelite.get("player_world")

        if pos:
            now = time.time()
            self.position_history.append((*pos, now))

            # Keep last 10 positions
            if len(self.position_history) > 10:
                self.position_history.pop(0)

            # Check if stuck
            if len(self.position_history) >= 5:
                recent = self.position_history[-5:]
                unique_positions = set((p[0], p[1], p[2]) for p in recent)

                if len(unique_positions) == 1:
                    return Obstacle(
                        obstacle_type=ObstacleType.UNKNOWN,
                        position=(0, 0),
                        can_bypass=False,
                    )

        return None

    def find_bypass_path(
        self,
        obstacle: Obstacle,
        current_pos: Tuple[int, int],
        target_pos: Tuple[int, int],
    ) -> List[Tuple[int, int]]:
        """
        Find a path around an obstacle.

        Returns a list of waypoints to navigate around the obstacle.
        """
        # Simple bypass: try going around
        dx = target_pos[0] - current_pos[0]
        dy = target_pos[1] - current_pos[1]

        waypoints = []

        if abs(dx) > abs(dy):
            # Horizontal movement blocked - try going around vertically
            waypoints.append((current_pos[0], current_pos[1] + 30))
            waypoints.append((target_pos[0], current_pos[1] + 30))
            waypoints.append(target_pos)
        else:
            # Vertical movement blocked - try going around horizontally
            waypoints.append((current_pos[0] + 30, current_pos[1]))
            waypoints.append((current_pos[0] + 30, target_pos[1]))
            waypoints.append(target_pos)

        return waypoints


# =============================================================================
# T7: LONG-DISTANCE NAVIGATION WITH LANDMARKS
# =============================================================================

@dataclass
class Landmark:
    """A recognizable location used for navigation."""
    name: str
    world_coords: Tuple[int, int, int]  # (x, y, plane)
    region: str
    hover_text_patterns: List[str] = field(default_factory=list)
    nearby_npcs: List[str] = field(default_factory=list)
    nearby_objects: List[str] = field(default_factory=list)


# Known landmarks for F2P areas
LANDMARKS = {
    # Lumbridge
    "lumbridge_castle": Landmark(
        name="Lumbridge Castle",
        world_coords=(3222, 3218, 0),
        region="Lumbridge",
        hover_text_patterns=["castle", "lumbridge"],
        nearby_npcs=["Duke Horacio", "Cook"],
    ),
    "lumbridge_church": Landmark(
        name="Lumbridge Church",
        world_coords=(3243, 3206, 0),
        region="Lumbridge",
        hover_text_patterns=["church", "altar"],
        nearby_npcs=["Father Aereck"],
    ),
    "lumbridge_bank": Landmark(
        name="Lumbridge Bank",
        world_coords=(3208, 3220, 2),
        region="Lumbridge",
        hover_text_patterns=["bank", "booth"],
    ),

    # Varrock
    "varrock_west_bank": Landmark(
        name="Varrock West Bank",
        world_coords=(3185, 3436, 0),
        region="Varrock",
        hover_text_patterns=["bank", "booth"],
    ),
    "varrock_east_bank": Landmark(
        name="Varrock East Bank",
        world_coords=(3253, 3420, 0),
        region="Varrock",
        hover_text_patterns=["bank", "booth"],
    ),
    "varrock_square": Landmark(
        name="Varrock Square",
        world_coords=(3212, 3428, 0),
        region="Varrock",
        hover_text_patterns=["fountain", "square"],
    ),

    # Falador
    "falador_east_bank": Landmark(
        name="Falador East Bank",
        world_coords=(3013, 3355, 0),
        region="Falador",
        hover_text_patterns=["bank", "booth"],
    ),
    "falador_west_bank": Landmark(
        name="Falador West Bank",
        world_coords=(2946, 3368, 0),
        region="Falador",
        hover_text_patterns=["bank", "booth"],
    ),

    # Al Kharid
    "al_kharid_bank": Landmark(
        name="Al Kharid Bank",
        world_coords=(3269, 3167, 0),
        region="Al Kharid",
        hover_text_patterns=["bank", "booth"],
    ),

    # Draynor
    "draynor_bank": Landmark(
        name="Draynor Bank",
        world_coords=(3092, 3245, 0),
        region="Draynor",
        hover_text_patterns=["bank", "booth"],
    ),

    # Tutorial Island
    "tutorial_start": Landmark(
        name="Tutorial Island Start",
        world_coords=(3094, 3107, 0),
        region="Tutorial Island",
        nearby_npcs=["Gielinor Guide"],
    ),
}


class LandmarkNavigator:
    """
    Navigate using landmarks for long distances (T7).

    Uses known landmarks to break long journeys into manageable segments.
    """

    def __init__(self):
        self.landmarks = LANDMARKS
        self.visited_landmarks: Set[str] = set()

    def find_nearest_landmark(
        self,
        current_pos: Tuple[int, int, int],
        target_region: Optional[str] = None,
    ) -> Optional[Landmark]:
        """Find the nearest landmark to current position."""
        best_landmark = None
        best_distance = float('inf')

        for name, landmark in self.landmarks.items():
            # Filter by region if specified
            if target_region and landmark.region != target_region:
                continue

            # Calculate distance
            dx = landmark.world_coords[0] - current_pos[0]
            dy = landmark.world_coords[1] - current_pos[1]
            distance = (dx ** 2 + dy ** 2) ** 0.5

            if distance < best_distance:
                best_distance = distance
                best_landmark = landmark

        return best_landmark

    def plan_route(
        self,
        start_pos: Tuple[int, int, int],
        end_pos: Tuple[int, int, int],
    ) -> List[Landmark]:
        """
        Plan a route using landmarks.

        Returns a list of landmarks to visit in order.
        """
        route = []
        current = start_pos

        # Find target region
        target_region = self._infer_region(end_pos)
        current_region = self._infer_region(start_pos)

        # If same region, direct navigation
        if target_region == current_region:
            return []

        # Find intermediate landmarks
        # This is a simplified version - a full implementation would use
        # proper pathfinding through connected regions
        if current_region and target_region:
            # Find a landmark in the target region
            for name, landmark in self.landmarks.items():
                if landmark.region == target_region:
                    route.append(landmark)
                    break

        return route

    def _infer_region(self, pos: Tuple[int, int, int]) -> str:
        """Infer region from world coordinates."""
        x, y, plane = pos

        # Tutorial Island
        if 3050 <= x <= 3150 and 3050 <= y <= 3150:
            return "Tutorial Island"

        # Lumbridge
        if 3200 <= x <= 3250 and 3200 <= y <= 3250:
            return "Lumbridge"

        # Varrock
        if 3180 <= x <= 3290 and 3380 <= y <= 3500:
            return "Varrock"

        # Falador
        if 2940 <= x <= 3040 and 3310 <= y <= 3400:
            return "Falador"

        # Draynor
        if 3080 <= x <= 3120 and 3230 <= y <= 3280:
            return "Draynor"

        # Al Kharid
        if 3270 <= x <= 3330 and 3140 <= y <= 3200:
            return "Al Kharid"

        return "unknown"


# =============================================================================
# T9: SMART ITEM ORGANIZATION
# =============================================================================

class ItemCategory(Enum):
    """Categories for inventory items."""
    FOOD = "food"
    POTION = "potion"
    TOOL = "tool"
    WEAPON = "weapon"
    ARMOR = "armor"
    RESOURCE = "resource"
    QUEST = "quest"
    JUNK = "junk"
    UNKNOWN = "unknown"


# Item categorization patterns
ITEM_CATEGORIES = {
    ItemCategory.FOOD: [
        "shrimp", "anchovies", "sardine", "herring", "mackerel",
        "trout", "salmon", "tuna", "lobster", "swordfish",
        "bread", "cake", "meat", "chicken", "beef", "pie",
    ],
    ItemCategory.POTION: [
        "potion", "vial", "dose", "restore", "prayer", "attack",
        "strength", "defence", "ranging", "magic", "antifire",
    ],
    ItemCategory.TOOL: [
        "axe", "pickaxe", "hammer", "chisel", "needle", "tinderbox",
        "knife", "saw", "spade", "rake", "secateurs",
    ],
    ItemCategory.WEAPON: [
        "sword", "scimitar", "mace", "battleaxe", "2h", "dagger",
        "bow", "crossbow", "staff", "wand",
    ],
    ItemCategory.ARMOR: [
        "helm", "full helm", "med helm", "chainbody", "platebody",
        "platelegs", "plateskirt", "shield", "boots", "gloves",
    ],
    ItemCategory.RESOURCE: [
        "ore", "bar", "log", "fish", "rune", "essence", "herb",
        "seed", "bone", "hide", "leather", "wool", "flax",
    ],
    ItemCategory.JUNK: [
        "burnt", "ashes", "empty", "broken", "old", "rusty",
    ],
}


class ItemOrganizer:
    """
    Smart inventory organization (T9).

    Organizes items by category and stacks similar items together.
    """

    def categorize_item(self, item_name: str) -> ItemCategory:
        """Determine the category of an item."""
        name_lower = item_name.lower()

        for category, patterns in ITEM_CATEGORIES.items():
            if any(pattern in name_lower for pattern in patterns):
                return category

        return ItemCategory.UNKNOWN

    def suggest_organization(
        self,
        inventory: List[Dict[str, Any]],
    ) -> Dict[int, int]:
        """
        Suggest moves to organize inventory.

        Returns a dict mapping from_slot -> to_slot for swaps.
        """
        moves = {}

        # Group items by category
        by_category: Dict[ItemCategory, List[Tuple[int, Dict]]] = {}
        for slot, item in enumerate(inventory):
            if item and item.get("name"):
                cat = self.categorize_item(item["name"])
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append((slot, item))

        # Suggested slot ranges for each category
        slot_ranges = {
            ItemCategory.FOOD: range(0, 7),      # First row
            ItemCategory.POTION: range(7, 14),   # Second row
            ItemCategory.TOOL: range(14, 18),    # Third row left
            ItemCategory.WEAPON: range(18, 21),  # Third row right
            ItemCategory.ARMOR: range(21, 24),   # Fourth row left
            ItemCategory.RESOURCE: range(24, 28),  # Fourth row right
        }

        # Generate moves to put items in their preferred ranges
        for category, items in by_category.items():
            if category not in slot_ranges:
                continue

            target_slots = list(slot_ranges[category])
            for i, (current_slot, item) in enumerate(items):
                if i < len(target_slots) and current_slot != target_slots[i]:
                    moves[current_slot] = target_slots[i]

        return moves

    def find_stackable_pairs(
        self,
        inventory: List[Dict[str, Any]],
    ) -> List[Tuple[int, int]]:
        """
        Find pairs of items that could be stacked.

        Returns list of (slot1, slot2) pairs that should be combined.
        """
        pairs = []

        # Group by item name
        by_name: Dict[str, List[int]] = {}
        for slot, item in enumerate(inventory):
            if item and item.get("name"):
                name = item["name"]
                if name not in by_name:
                    by_name[name] = []
                by_name[name].append(slot)

        # Find items that appear in multiple slots
        for name, slots in by_name.items():
            if len(slots) >= 2:
                # Pair up slots for stacking
                for i in range(0, len(slots) - 1, 2):
                    pairs.append((slots[i], slots[i + 1]))

        return pairs


# =============================================================================
# T10: GOAL-BASED ACTIVITY SELECTION
# =============================================================================

class GoalType(Enum):
    """Types of goals."""
    SKILL_LEVEL = "skill_level"
    QUEST_COMPLETE = "quest_complete"
    ITEM_ACQUIRE = "item_acquire"
    GOLD_AMOUNT = "gold_amount"
    COMBAT_LEVEL = "combat_level"


@dataclass
class Goal:
    """A player goal."""
    goal_type: GoalType
    target: str  # Skill name, quest name, item name, etc.
    target_value: int  # Level, quantity, etc.
    priority: int = 1  # 1 = highest priority
    deadline: Optional[datetime] = None


@dataclass
class Activity:
    """An in-game activity to achieve a goal."""
    name: str
    description: str
    skills_trained: List[str]
    xp_per_hour: Dict[str, int]  # skill -> xp/hr estimate
    requirements: Dict[str, int]  # skill -> level requirement
    f2p: bool = True
    location: str = ""


# Known F2P activities
F2P_ACTIVITIES = [
    Activity(
        name="chop_trees",
        description="Chop normal trees near Lumbridge",
        skills_trained=["woodcutting"],
        xp_per_hour={"woodcutting": 10000},
        requirements={"woodcutting": 1},
        location="Lumbridge",
    ),
    Activity(
        name="chop_oaks",
        description="Chop oak trees near Varrock West Bank",
        skills_trained=["woodcutting"],
        xp_per_hour={"woodcutting": 20000},
        requirements={"woodcutting": 15},
        location="Varrock",
    ),
    Activity(
        name="chop_willows",
        description="Chop willow trees at Draynor",
        skills_trained=["woodcutting"],
        xp_per_hour={"woodcutting": 35000},
        requirements={"woodcutting": 30},
        location="Draynor",
    ),
    Activity(
        name="fish_shrimp",
        description="Fish shrimp at Lumbridge Swamp",
        skills_trained=["fishing"],
        xp_per_hour={"fishing": 5000},
        requirements={"fishing": 1},
        location="Lumbridge",
    ),
    Activity(
        name="fish_trout",
        description="Fish trout at Barbarian Village",
        skills_trained=["fishing"],
        xp_per_hour={"fishing": 20000},
        requirements={"fishing": 20},
        location="Barbarian Village",
    ),
    Activity(
        name="mine_tin_copper",
        description="Mine tin and copper at Lumbridge Swamp",
        skills_trained=["mining"],
        xp_per_hour={"mining": 10000},
        requirements={"mining": 1},
        location="Lumbridge",
    ),
    Activity(
        name="mine_iron",
        description="Mine iron ore at Al Kharid or Varrock",
        skills_trained=["mining"],
        xp_per_hour={"mining": 25000},
        requirements={"mining": 15},
        location="Al Kharid",
    ),
    Activity(
        name="kill_cows",
        description="Kill cows for combat XP and cowhides",
        skills_trained=["attack", "strength", "defence"],
        xp_per_hour={"attack": 15000, "strength": 15000, "defence": 15000},
        requirements={"attack": 1},
        location="Lumbridge",
    ),
    Activity(
        name="kill_chickens",
        description="Kill chickens for easy combat XP",
        skills_trained=["attack", "strength", "defence"],
        xp_per_hour={"attack": 5000, "strength": 5000, "defence": 5000},
        requirements={"attack": 1},
        location="Lumbridge",
    ),
]


class GoalBasedPlanner:
    """
    Goal-based activity selection (T10).

    Selects the best activity to achieve the player's goals.
    """

    def __init__(self):
        self.goals: List[Goal] = []
        self.activities = F2P_ACTIVITIES

    def add_goal(self, goal: Goal):
        """Add a goal."""
        self.goals.append(goal)
        self.goals.sort(key=lambda g: g.priority)

    def remove_goal(self, goal_type: GoalType, target: str):
        """Remove a goal."""
        self.goals = [
            g for g in self.goals
            if not (g.goal_type == goal_type and g.target == target)
        ]

    def select_activity(
        self,
        current_skills: Dict[str, int],
    ) -> Optional[Activity]:
        """
        Select the best activity based on current goals and skills.

        Args:
            current_skills: Current skill levels

        Returns:
            Best activity to perform, or None if no suitable activity
        """
        if not self.goals:
            return None

        # Focus on highest priority goal
        primary_goal = self.goals[0]

        if primary_goal.goal_type == GoalType.SKILL_LEVEL:
            target_skill = primary_goal.target.lower()
            target_level = primary_goal.target_value
            current_level = current_skills.get(target_skill, 1)

            if current_level >= target_level:
                # Goal achieved!
                self.goals.pop(0)
                return self.select_activity(current_skills)

            # Find activities that train this skill
            suitable = []
            for activity in self.activities:
                if target_skill in [s.lower() for s in activity.skills_trained]:
                    # Check requirements
                    meets_reqs = all(
                        current_skills.get(skill, 1) >= level
                        for skill, level in activity.requirements.items()
                    )
                    if meets_reqs:
                        suitable.append(activity)

            if suitable:
                # Pick the one with highest XP rate for target skill
                return max(
                    suitable,
                    key=lambda a: a.xp_per_hour.get(target_skill, 0)
                )

        return None

    def estimate_time_to_goal(
        self,
        goal: Goal,
        current_skills: Dict[str, int],
    ) -> Optional[timedelta]:
        """Estimate time to achieve a goal."""
        if goal.goal_type != GoalType.SKILL_LEVEL:
            return None

        target_skill = goal.target.lower()
        current_level = current_skills.get(target_skill, 1)
        target_level = goal.target_value

        if current_level >= target_level:
            return timedelta(seconds=0)

        # Find best activity
        activity = self.select_activity(current_skills)
        if not activity:
            return None

        xp_rate = activity.xp_per_hour.get(target_skill, 0)
        if xp_rate == 0:
            return None

        # Simple XP calculation (would need actual XP tables for accuracy)
        current_xp = current_level * 100  # Rough estimate
        target_xp = target_level * 150    # Rough estimate
        xp_needed = target_xp - current_xp

        hours = xp_needed / xp_rate
        return timedelta(hours=hours)


# =============================================================================
# T11: DAILY TASK ROTATION
# =============================================================================

@dataclass
class DailyTask:
    """A daily task to complete."""
    name: str
    activity: str
    duration_minutes: int
    priority: int
    completed_today: bool = False
    last_completed: Optional[datetime] = None


class DailyRotation:
    """
    Daily task rotation system (T11).

    Manages a rotation of tasks to complete each day.
    """

    def __init__(self):
        self.tasks: List[DailyTask] = []
        self.current_task_index: int = 0

    def add_task(self, task: DailyTask):
        """Add a daily task."""
        self.tasks.append(task)
        self.tasks.sort(key=lambda t: t.priority)

    def get_next_task(self) -> Optional[DailyTask]:
        """Get the next incomplete task."""
        for task in self.tasks:
            if not task.completed_today:
                return task
        return None

    def complete_task(self, task_name: str):
        """Mark a task as completed."""
        for task in self.tasks:
            if task.name == task_name:
                task.completed_today = True
                task.last_completed = datetime.now()
                break

    def reset_daily_tasks(self):
        """Reset all tasks for a new day."""
        for task in self.tasks:
            task.completed_today = False

    def should_reset(self) -> bool:
        """Check if tasks should be reset (new day)."""
        if not self.tasks:
            return False

        # Check if any task was last completed yesterday or earlier
        today = datetime.now().date()
        for task in self.tasks:
            if task.last_completed and task.last_completed.date() < today:
                return True

        return False


# =============================================================================
# T12: PRAYER FLICKING SUPPORT
# =============================================================================

class PrayerType(Enum):
    """Types of prayers."""
    PROTECT_MELEE = "protect_melee"
    PROTECT_MISSILES = "protect_missiles"
    PROTECT_MAGIC = "protect_magic"
    THICK_SKIN = "thick_skin"
    BURST_OF_STRENGTH = "burst_of_strength"
    CLARITY_OF_THOUGHT = "clarity_of_thought"
    ROCK_SKIN = "rock_skin"
    SUPERHUMAN_STRENGTH = "superhuman_strength"
    IMPROVED_REFLEXES = "improved_reflexes"


# Prayer key bindings (approximate F-key positions)
PRAYER_POSITIONS = {
    PrayerType.THICK_SKIN: (0, 0),
    PrayerType.BURST_OF_STRENGTH: (1, 0),
    PrayerType.CLARITY_OF_THOUGHT: (2, 0),
    PrayerType.ROCK_SKIN: (0, 1),
    PrayerType.SUPERHUMAN_STRENGTH: (1, 1),
    PrayerType.IMPROVED_REFLEXES: (2, 1),
    PrayerType.PROTECT_MAGIC: (0, 4),
    PrayerType.PROTECT_MISSILES: (1, 4),
    PrayerType.PROTECT_MELEE: (2, 4),
}


class PrayerFlicker:
    """
    Prayer flicking support (T12).

    Implements prayer flicking to conserve prayer points.
    """

    def __init__(self):
        self.active_prayers: Set[PrayerType] = set()
        self.flicking_enabled: bool = False
        self.flick_interval_ms: int = 600  # Game tick
        self.last_flick_time: float = 0.0

    def start_flicking(self, prayer: PrayerType):
        """Start flicking a prayer."""
        self.active_prayers.add(prayer)
        self.flicking_enabled = True

    def stop_flicking(self, prayer: Optional[PrayerType] = None):
        """Stop flicking a prayer or all prayers."""
        if prayer:
            self.active_prayers.discard(prayer)
        else:
            self.active_prayers.clear()

        if not self.active_prayers:
            self.flicking_enabled = False

    def should_flick(self) -> bool:
        """Check if it's time to flick prayers."""
        if not self.flicking_enabled:
            return False

        now = time.time()
        elapsed_ms = (now - self.last_flick_time) * 1000

        return elapsed_ms >= self.flick_interval_ms

    def get_prayer_position(
        self,
        prayer: PrayerType,
        prayer_tab_bounds: Tuple[int, int, int, int],
    ) -> Tuple[int, int]:
        """Get screen position of a prayer icon."""
        px, py = PRAYER_POSITIONS.get(prayer, (0, 0))

        tab_x, tab_y, tab_w, tab_h = prayer_tab_bounds

        icon_width = 34
        icon_height = 34

        x = tab_x + 10 + px * icon_width + icon_width // 2
        y = tab_y + 10 + py * icon_height + icon_height // 2

        return (x, y)


# =============================================================================
# T13, T14: RANDOM EVENT HANDLERS (Quiz Master, Frog Princess)
# =============================================================================

@dataclass
class RandomEvent:
    """A detected random event."""
    name: str
    npc_name: str
    position: Optional[Tuple[int, int]] = None
    requires_interaction: bool = True
    is_dangerous: bool = False


class QuizMasterHandler:
    """
    Quiz Master random event handler (T13).

    Handles the Quiz Master random event by answering questions.
    """

    # Common quiz answers (item -> category)
    QUIZ_ANSWERS = {
        # Category: Things that are worn
        "boots": "wear",
        "gloves": "wear",
        "helmet": "wear",
        "platebody": "wear",
        "shield": "wear",

        # Category: Things used for combat
        "sword": "combat",
        "bow": "combat",
        "arrows": "combat",
        "runes": "combat",

        # Category: Things used for fishing
        "rod": "fishing",
        "net": "fishing",
        "harpoon": "fishing",
        "bait": "fishing",

        # Category: Things that are food
        "fish": "food",
        "bread": "food",
        "cake": "food",
        "meat": "food",
    }

    def detect_quiz_master(self, snapshot: Dict[str, Any]) -> bool:
        """Detect if Quiz Master is present."""
        npcs = snapshot.get("runelite_data", {}).get("npcs_on_screen", [])

        for npc in npcs:
            if "quiz" in npc.get("name", "").lower():
                return True

        return False

    def answer_question(
        self,
        question_text: str,
        options: List[str],
    ) -> int:
        """
        Answer a quiz question.

        Args:
            question_text: The question being asked
            options: Available answer options

        Returns:
            Index of the correct answer (1-based)
        """
        question_lower = question_text.lower()

        # Try to identify the category being asked about
        category = None
        if "wear" in question_lower or "worn" in question_lower:
            category = "wear"
        elif "combat" in question_lower or "fight" in question_lower:
            category = "combat"
        elif "fish" in question_lower:
            category = "fishing"
        elif "eat" in question_lower or "food" in question_lower:
            category = "food"

        if category:
            # Find matching option
            for i, option in enumerate(options):
                option_lower = option.lower()
                for item, item_cat in self.QUIZ_ANSWERS.items():
                    if item in option_lower and item_cat == category:
                        return i + 1

        # Default to first option if unsure
        return 1


class FrogPrincessHandler:
    """
    Frog Princess random event handler (T14).

    Handles the Frog Princess/Prince random event.
    """

    def detect_frog_event(self, snapshot: Dict[str, Any]) -> bool:
        """Detect if Frog Princess/Prince event is active."""
        npcs = snapshot.get("runelite_data", {}).get("npcs_on_screen", [])

        for npc in npcs:
            name = npc.get("name", "").lower()
            if "frog" in name and ("princess" in name or "prince" in name):
                return True

        return False

    def get_kiss_target(self, snapshot: Dict[str, Any]) -> Optional[Tuple[int, int]]:
        """Get the position of the frog to kiss."""
        npcs = snapshot.get("runelite_data", {}).get("npcs_on_screen", [])

        for npc in npcs:
            name = npc.get("name", "").lower()
            if "frog" in name and ("princess" in name or "prince" in name):
                x = npc.get("x") or npc.get("screen_x")
                y = npc.get("y") or npc.get("screen_y")
                if x and y:
                    return (x, y)

        return None


# =============================================================================
# T15: SAFE-SPOT DETECTION
# =============================================================================

@dataclass
class SafeSpot:
    """A location where the player can safely attack without being hit."""
    position: Tuple[int, int]  # Screen coordinates
    world_position: Optional[Tuple[int, int, int]] = None
    blocking_object: str = ""  # What object provides safety
    valid_targets: List[str] = field(default_factory=list)  # NPCs that can be safely attacked


class SafeSpotDetector:
    """
    Safe-spot detection for combat (T15).

    Identifies locations where the player can attack NPCs safely.
    """

    # Known safe-spot locations
    KNOWN_SAFE_SPOTS = {
        "varrock_dark_wizards": SafeSpot(
            position=(0, 0),
            world_position=(3227, 3367, 0),
            blocking_object="fence",
            valid_targets=["dark wizard"],
        ),
        "lumbridge_cows": SafeSpot(
            position=(0, 0),
            world_position=(3253, 3299, 0),
            blocking_object="fence",
            valid_targets=["cow"],
        ),
    }

    def find_safe_spot(
        self,
        current_pos: Tuple[int, int, int],
        target_npc: str,
    ) -> Optional[SafeSpot]:
        """Find a safe spot for attacking a target NPC."""
        target_lower = target_npc.lower()

        for name, spot in self.KNOWN_SAFE_SPOTS.items():
            if target_lower in [t.lower() for t in spot.valid_targets]:
                # Check if we're close enough to use this spot
                if spot.world_position:
                    dx = abs(spot.world_position[0] - current_pos[0])
                    dy = abs(spot.world_position[1] - current_pos[1])
                    if dx < 50 and dy < 50:
                        return spot

        return None

    def detect_dynamic_safe_spot(
        self,
        snapshot: Dict[str, Any],
        target_npc_pos: Tuple[int, int],
    ) -> Optional[SafeSpot]:
        """
        Try to detect a dynamic safe spot based on current game state.

        Looks for objects between player and NPC that could provide cover.
        """
        # This would require more sophisticated object detection
        # For now, return None and rely on known safe spots
        return None


# =============================================================================
# T16: RESOURCE AVAILABILITY SCANNING
# =============================================================================

@dataclass
class Resource:
    """A gatherable resource."""
    name: str
    resource_type: str  # "tree", "rock", "fishing_spot", etc.
    position: Tuple[int, int]  # Screen coordinates
    world_position: Optional[Tuple[int, int, int]] = None
    is_available: bool = True
    respawn_time_seconds: float = 0.0


class ResourceScanner:
    """
    Resource availability scanning (T16).

    Scans for available resources in the area.
    """

    # Resource patterns in hover text
    RESOURCE_PATTERNS = {
        "tree": {
            "patterns": ["chop", "tree", "oak", "willow", "yew", "magic"],
            "depleted": ["stump", "tree stump"],
        },
        "rock": {
            "patterns": ["mine", "rock", "ore", "tin", "copper", "iron", "coal", "mithril"],
            "depleted": ["empty", "depleted", "rocks"],
        },
        "fishing_spot": {
            "patterns": ["fish", "net", "lure", "bait", "harpoon", "cage"],
            "depleted": [],  # Fishing spots move, don't deplete
        },
    }

    def __init__(self):
        self.known_resources: Dict[str, Resource] = {}
        self.last_scan_time: float = 0.0

    def scan_area(
        self,
        snapshot: Dict[str, Any],
        hover_fn: Optional[Callable[[int, int], str]] = None,
    ) -> List[Resource]:
        """
        Scan the current area for resources.

        Args:
            snapshot: Current game snapshot
            hover_fn: Optional function to get hover text at a position

        Returns:
            List of detected resources
        """
        resources = []

        # Check RuneLite data for objects
        runelite = snapshot.get("runelite_data", {})
        objects = runelite.get("objects", [])

        for obj in objects:
            name = obj.get("name", "").lower()

            for res_type, patterns in self.RESOURCE_PATTERNS.items():
                if any(p in name for p in patterns["patterns"]):
                    # Check if depleted
                    is_available = not any(d in name for d in patterns["depleted"])

                    resource = Resource(
                        name=obj.get("name", "unknown"),
                        resource_type=res_type,
                        position=(obj.get("x", 0), obj.get("y", 0)),
                        is_available=is_available,
                    )
                    resources.append(resource)

                    # Track in known resources
                    key = f"{res_type}_{resource.position}"
                    self.known_resources[key] = resource

        self.last_scan_time = time.time()
        return resources

    def get_nearest_available(
        self,
        resource_type: str,
        current_pos: Tuple[int, int],
    ) -> Optional[Resource]:
        """Get the nearest available resource of a given type."""
        best_resource = None
        best_distance = float('inf')

        for key, resource in self.known_resources.items():
            if resource.resource_type != resource_type:
                continue
            if not resource.is_available:
                continue

            dx = resource.position[0] - current_pos[0]
            dy = resource.position[1] - current_pos[1]
            distance = (dx ** 2 + dy ** 2) ** 0.5

            if distance < best_distance:
                best_distance = distance
                best_resource = resource

        return best_resource

    def mark_depleted(self, position: Tuple[int, int]):
        """Mark a resource as depleted."""
        for key, resource in self.known_resources.items():
            if resource.position == position:
                resource.is_available = False
                break

    def refresh_availability(self):
        """Refresh resource availability based on respawn times."""
        now = time.time()

        for resource in self.known_resources.values():
            if not resource.is_available and resource.respawn_time_seconds > 0:
                # Check if enough time has passed for respawn
                # This is a simplified version - actual implementation would
                # track when each resource was depleted
                resource.is_available = True


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # T6: Obstacle detection
    "ObstacleType",
    "Obstacle",
    "ObstacleDetector",

    # T7: Landmark navigation
    "Landmark",
    "LANDMARKS",
    "LandmarkNavigator",

    # T9: Item organization
    "ItemCategory",
    "ItemOrganizer",

    # T10: Goal-based planning
    "GoalType",
    "Goal",
    "Activity",
    "GoalBasedPlanner",

    # T11: Daily rotation
    "DailyTask",
    "DailyRotation",

    # T12: Prayer flicking
    "PrayerType",
    "PrayerFlicker",

    # T13: Quiz master
    "QuizMasterHandler",

    # T14: Frog princess
    "FrogPrincessHandler",

    # T15: Safe spots
    "SafeSpot",
    "SafeSpotDetector",

    # T16: Resource scanning
    "Resource",
    "ResourceScanner",
]
