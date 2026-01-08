"""
Unified Tool Dispatcher - Wires all interaction features into the canonical loop.

This module provides:
- Centralized registration of all agent tools
- Fast dispatch to appropriate handlers
- Integration of autonomy_features.py into the main loop
- Priority-based feature activation (prayer, safe spots, random events)

Nightfall - 2026-01-07
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# TOOL REGISTRY
# =============================================================================

class ToolCategory(Enum):
    """Categories of tools."""
    COMBAT = "combat"
    NAVIGATION = "navigation"
    SKILLING = "skilling"
    BANKING = "banking"
    DIALOGUE = "dialogue"
    RANDOM_EVENT = "random_event"
    UTILITY = "utility"
    ADVANCED = "advanced"


@dataclass
class ToolDefinition:
    """Definition of an agent tool."""
    name: str
    category: ToolCategory
    handler: Callable[..., Any]
    description: str = ""
    requires_snapshot: bool = True
    priority: int = 0  # Higher = executed first


class ToolRegistry:
    """
    Central registry for all agent tools.

    Provides fast lookup and dispatch to tool handlers.
    """

    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self.categories: Dict[ToolCategory, List[str]] = {cat: [] for cat in ToolCategory}
        self._initialized = False

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool."""
        self.tools[tool.name] = tool
        self.categories[tool.category].append(tool.name)
        logger.debug(f"Registered tool: {tool.name} [{tool.category.value}]")

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self.tools.get(name)

    def list_tools(self, category: Optional[ToolCategory] = None) -> List[str]:
        """List available tools."""
        if category:
            return self.categories.get(category, [])
        return list(self.tools.keys())

    def dispatch(
        self,
        tool_name: str,
        *args,
        **kwargs,
    ) -> Any:
        """
        Dispatch to a tool handler.

        Returns the result of the tool execution.
        """
        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")

        return tool.handler(*args, **kwargs)


# Global registry instance
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _registry


# =============================================================================
# INTEGRATED FEATURE MANAGER
# =============================================================================

class FeatureManager:
    """
    Manages all integrated features and their state.

    Connects autonomy_features.py classes to the main loop.
    """

    def __init__(self, window_bounds: Tuple[int, int, int, int], snapshot_fn: Callable[[], Dict]):
        self.window_bounds = window_bounds
        self.snapshot_fn = snapshot_fn

        # Import and initialize features
        self._init_features()

    def _init_features(self) -> None:
        """Initialize all feature handlers."""
        # Import autonomy features
        try:
            from src.autonomy_features import (
                ObstacleDetector,
                LandmarkNavigator,
                ItemOrganizer,
                GoalBasedPlanner,
                DailyRotation,
                PrayerFlicker,
                QuizMasterHandler,
                FrogPrincessHandler,
                SafeSpotDetector,
                ResourceScanner,
            )

            self.obstacle_detector = ObstacleDetector()
            self.landmark_navigator = LandmarkNavigator()
            self.item_organizer = ItemOrganizer()
            self.goal_planner = GoalBasedPlanner()
            self.daily_rotation = DailyRotation()
            self.prayer_flicker = PrayerFlicker()
            self.quiz_handler = QuizMasterHandler()
            self.frog_handler = FrogPrincessHandler()
            self.safe_spot_detector = SafeSpotDetector()
            self.resource_scanner = ResourceScanner()

            logger.info("Autonomy features initialized")
        except ImportError as e:
            logger.warning(f"Could not import autonomy_features: {e}")
            self._set_feature_stubs()

        # Import standard autonomy
        try:
            from src.autonomy import (
                SkillingLoop,
                CombatLoop,
                BankTrip,
                XPTracker,
                ActivityScheduler,
            )

            self.xp_tracker = XPTracker()
            self.activity_scheduler = ActivityScheduler()
            self.active_skilling_loop: Optional[SkillingLoop] = None
            self.active_combat_loop: Optional[CombatLoop] = None
            self.active_bank_trip: Optional[BankTrip] = None

            logger.info("Standard autonomy initialized")
        except ImportError as e:
            logger.warning(f"Could not import autonomy: {e}")

    def _set_feature_stubs(self) -> None:
        """Set stub objects when features unavailable."""
        self.obstacle_detector = None
        self.landmark_navigator = None
        self.item_organizer = None
        self.goal_planner = None
        self.daily_rotation = None
        self.prayer_flicker = None
        self.quiz_handler = None
        self.frog_handler = None
        self.safe_spot_detector = None
        self.resource_scanner = None

    # =========================================================================
    # PRAYER FLICKING
    # =========================================================================

    def start_prayer_flicking(self, prayer_name: str) -> bool:
        """Start flicking a prayer."""
        if not self.prayer_flicker:
            return False

        from src.autonomy_features import PrayerType

        prayer_map = {
            "protect_melee": PrayerType.PROTECT_MELEE,
            "protect_missiles": PrayerType.PROTECT_MISSILES,
            "protect_magic": PrayerType.PROTECT_MAGIC,
            "thick_skin": PrayerType.THICK_SKIN,
            "burst_of_strength": PrayerType.BURST_OF_STRENGTH,
            "superhuman_strength": PrayerType.SUPERHUMAN_STRENGTH,
        }

        prayer = prayer_map.get(prayer_name.lower())
        if prayer:
            self.prayer_flicker.start_flicking(prayer)
            return True
        return False

    def stop_prayer_flicking(self) -> None:
        """Stop all prayer flicking."""
        if self.prayer_flicker:
            self.prayer_flicker.stop_flicking()

    def tick_prayer_flicking(self, snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Tick prayer flicking - returns action if flick needed.

        Returns:
            Dict with action details if flick needed, None otherwise
        """
        if not self.prayer_flicker or not self.prayer_flicker.should_flick():
            return None

        # Get prayer tab bounds from snapshot
        roi = snapshot.get("roi", {})
        prayer_tab = roi.get("prayer", {"x": 560, "y": 210, "width": 180, "height": 260})

        actions = []
        for prayer in self.prayer_flicker.active_prayers:
            pos = self.prayer_flicker.get_prayer_position(
                prayer,
                (prayer_tab["x"], prayer_tab["y"], prayer_tab["width"], prayer_tab["height"])
            )
            actions.append({
                "type": "click",
                "target": {"x": pos[0], "y": pos[1]},
                "prayer": prayer.value,
            })

        self.prayer_flicker.last_flick_time = time.time()
        return {"action": "prayer_flick", "clicks": actions}

    # =========================================================================
    # SAFE SPOTS
    # =========================================================================

    def find_safe_spot(
        self,
        target_npc: str,
        snapshot: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Find a safe spot for attacking an NPC."""
        if not self.safe_spot_detector:
            return None

        runelite = snapshot.get("runelite_data", {})
        player_world = runelite.get("player_world")

        if not player_world:
            return None

        spot = self.safe_spot_detector.find_safe_spot(tuple(player_world), target_npc)
        if spot:
            return {
                "position": spot.position,
                "world_position": spot.world_position,
                "blocking_object": spot.blocking_object,
            }
        return None

    # =========================================================================
    # RANDOM EVENTS
    # =========================================================================

    def handle_random_event(self, snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check and handle random events.

        Returns action dict if event detected and handled.
        """
        # Check for quiz master
        if self.quiz_handler and self.quiz_handler.detect_quiz_master(snapshot):
            # Get question from dialogue
            ui = snapshot.get("ui", {})
            dialogue_text = " ".join(ui.get("dialogue_options", []))

            if dialogue_text:
                answer = self.quiz_handler.answer_question(
                    dialogue_text,
                    ui.get("dialogue_options", [])
                )
                return {
                    "action": "random_event",
                    "event_type": "quiz_master",
                    "answer_option": answer,
                }

        # Check for frog princess
        if self.frog_handler and self.frog_handler.detect_frog_event(snapshot):
            target = self.frog_handler.get_kiss_target(snapshot)
            if target:
                return {
                    "action": "random_event",
                    "event_type": "frog_princess",
                    "target": {"x": target[0], "y": target[1]},
                }

        return None

    # =========================================================================
    # NAVIGATION
    # =========================================================================

    def check_obstacle(
        self,
        snapshot: Dict[str, Any],
        target_direction: Tuple[int, int],
    ) -> Optional[Dict[str, Any]]:
        """Check for obstacles in a direction."""
        if not self.obstacle_detector:
            return None

        obstacle = self.obstacle_detector.detect_obstacle(snapshot, target_direction)
        if obstacle:
            return {
                "obstacle_type": obstacle.obstacle_type.value,
                "can_bypass": obstacle.can_bypass,
                "bypass_action": obstacle.bypass_action,
            }
        return None

    def navigate_to_landmark(
        self,
        target_landmark: str,
        snapshot: Dict[str, Any],
    ) -> Optional[List[Dict[str, Any]]]:
        """Get navigation waypoints to a landmark."""
        if not self.landmark_navigator:
            return None

        from src.autonomy_features import LANDMARKS

        landmark = LANDMARKS.get(target_landmark)
        if not landmark:
            return None

        runelite = snapshot.get("runelite_data", {})
        player_world = runelite.get("player_world")

        if not player_world:
            return None

        route = self.landmark_navigator.plan_route(
            tuple(player_world),
            landmark.world_coords
        )

        return [
            {"name": lm.name, "coords": lm.world_coords}
            for lm in route
        ]

    # =========================================================================
    # RESOURCE SCANNING
    # =========================================================================

    def scan_resources(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scan for nearby resources."""
        if not self.resource_scanner:
            return []

        resources = self.resource_scanner.scan_area(snapshot)
        return [
            {
                "name": r.name,
                "type": r.resource_type,
                "position": r.position,
                "available": r.is_available,
            }
            for r in resources
        ]

    def get_nearest_resource(
        self,
        resource_type: str,
        snapshot: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Get the nearest available resource of a type."""
        if not self.resource_scanner:
            return None

        runelite = snapshot.get("runelite_data", {})
        player_pos = runelite.get("player_screen")

        if not player_pos:
            return None

        resource = self.resource_scanner.get_nearest_available(
            resource_type,
            tuple(player_pos)
        )

        if resource:
            return {
                "name": resource.name,
                "type": resource.resource_type,
                "position": resource.position,
                "available": resource.is_available,
            }
        return None

    # =========================================================================
    # GOAL-BASED PLANNING
    # =========================================================================

    def add_goal(
        self,
        goal_type: str,
        target: str,
        target_value: int,
        priority: int = 1,
    ) -> bool:
        """Add a goal to the planner."""
        if not self.goal_planner:
            return False

        from src.autonomy_features import Goal, GoalType

        type_map = {
            "skill_level": GoalType.SKILL_LEVEL,
            "quest": GoalType.QUEST_COMPLETE,
            "item": GoalType.ITEM_ACQUIRE,
            "gold": GoalType.GOLD_AMOUNT,
            "combat_level": GoalType.COMBAT_LEVEL,
        }

        gtype = type_map.get(goal_type.lower())
        if not gtype:
            return False

        goal = Goal(
            goal_type=gtype,
            target=target,
            target_value=target_value,
            priority=priority,
        )
        self.goal_planner.add_goal(goal)
        return True

    def get_recommended_activity(
        self,
        snapshot: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Get recommended activity based on goals."""
        if not self.goal_planner:
            return None

        # Get current skills from snapshot
        account = snapshot.get("account", {})
        skills = account.get("skills", {})

        current_skills = {}
        for skill_name, data in skills.items():
            if isinstance(data, dict):
                current_skills[skill_name.lower()] = data.get("level", 1)
            elif isinstance(data, int):
                current_skills[skill_name.lower()] = data

        activity = self.goal_planner.select_activity(current_skills)
        if activity:
            return {
                "name": activity.name,
                "description": activity.description,
                "skills_trained": activity.skills_trained,
                "xp_per_hour": activity.xp_per_hour,
                "location": activity.location,
            }
        return None


# =============================================================================
# REGISTER ALL TOOLS
# =============================================================================

def register_all_tools(
    registry: ToolRegistry,
    feature_manager: FeatureManager,
) -> None:
    """Register all available tools with the registry."""

    # Combat tools
    registry.register(ToolDefinition(
        name="start_prayer_flick",
        category=ToolCategory.COMBAT,
        handler=feature_manager.start_prayer_flicking,
        description="Start flicking a prayer (protect_melee, protect_missiles, etc.)",
        priority=10,
    ))

    registry.register(ToolDefinition(
        name="stop_prayer_flick",
        category=ToolCategory.COMBAT,
        handler=feature_manager.stop_prayer_flicking,
        description="Stop all prayer flicking",
        priority=10,
    ))

    registry.register(ToolDefinition(
        name="find_safe_spot",
        category=ToolCategory.COMBAT,
        handler=feature_manager.find_safe_spot,
        description="Find a safe spot for attacking an NPC",
        priority=5,
    ))

    # Navigation tools
    registry.register(ToolDefinition(
        name="check_obstacle",
        category=ToolCategory.NAVIGATION,
        handler=feature_manager.check_obstacle,
        description="Check for obstacles in a direction",
        priority=5,
    ))

    registry.register(ToolDefinition(
        name="navigate_to_landmark",
        category=ToolCategory.NAVIGATION,
        handler=feature_manager.navigate_to_landmark,
        description="Get waypoints to a known landmark",
        priority=3,
    ))

    # Random event tools
    registry.register(ToolDefinition(
        name="handle_random_event",
        category=ToolCategory.RANDOM_EVENT,
        handler=feature_manager.handle_random_event,
        description="Detect and handle random events",
        priority=100,  # High priority
    ))

    # Skilling tools
    registry.register(ToolDefinition(
        name="scan_resources",
        category=ToolCategory.SKILLING,
        handler=feature_manager.scan_resources,
        description="Scan area for gatherable resources",
        priority=2,
    ))

    registry.register(ToolDefinition(
        name="get_nearest_resource",
        category=ToolCategory.SKILLING,
        handler=feature_manager.get_nearest_resource,
        description="Find nearest available resource of a type",
        priority=3,
    ))

    # Planning tools
    registry.register(ToolDefinition(
        name="add_goal",
        category=ToolCategory.UTILITY,
        handler=feature_manager.add_goal,
        description="Add a goal to the activity planner",
        priority=1,
    ))

    registry.register(ToolDefinition(
        name="get_recommended_activity",
        category=ToolCategory.UTILITY,
        handler=feature_manager.get_recommended_activity,
        description="Get recommended activity based on goals",
        priority=2,
    ))


# =============================================================================
# PRIORITY TICK SYSTEM
# =============================================================================

class PriorityTickSystem:
    """
    Runs priority checks each tick.

    Priority order:
    1. Random events (must be handled immediately)
    2. Prayer flicking (time-sensitive)
    3. Health check (eat food)
    4. Obstacle check (when moving)
    5. Regular actions
    """

    def __init__(self, feature_manager: FeatureManager):
        self.feature_manager = feature_manager

    def tick(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Run all priority checks.

        Returns list of priority actions to take (in order).
        """
        actions = []

        # Priority 1: Random events
        event_action = self.feature_manager.handle_random_event(snapshot)
        if event_action:
            actions.append(event_action)

        # Priority 2: Prayer flicking
        prayer_action = self.feature_manager.tick_prayer_flicking(snapshot)
        if prayer_action:
            actions.append(prayer_action)

        # Priority 3: Health check (delegated to caller for now)

        return actions


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ToolRegistry",
    "ToolDefinition",
    "ToolCategory",
    "FeatureManager",
    "PriorityTickSystem",
    "get_registry",
    "register_all_tools",
]
