"""
Autonomous Agent - Complete integration of all systems.

This is the main agent loop that:
1. Captures game state (eyes)
2. Asks the local model for a decision (brain)
3. Executes the command (hands)
4. Validates and repeats

Integrated features:
- snapshot_schema.py: SNAPSHOT_SCHEMA.md compliant capture with fallback triggers
- autonomy_features.py: Prayer flicking, safe spots, quiz/frog handlers, goal planning
- agent_tools.py: Timing variance, human-like jitter

Usage:
    python -m src.autonomous_agent --goal "complete tutorial island"
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

from src.perception import find_window

# Use schema-compliant snapshot when available, fallback to fast_perception
try:
    from src.snapshot_schema import capture_snapshot_v2, get_fallback_trigger
    USE_SCHEMA_SNAPSHOT = True
except ImportError:
    from src.fast_perception import capture_snapshot as capture_snapshot_v2
    USE_SCHEMA_SNAPSHOT = False
    get_fallback_trigger = lambda: None

from src.local_model import run_local_model
from src.agent_commands import (
    AgentCommander,
    parse_model_command,
    get_available_commands,
    get_context_for_model,
)
from src.autonomy import (
    detect_random_event,
    handle_random_event,
    is_inventory_full,
    get_health_percent,
    detect_death,
    is_player_idle,
)
from src.game_actions import (
    detect_dialogue_state,
    DialogueState,
    press_dialogue_continue,
    press_dialogue_option,
    handle_dialogue_keyboard,
    get_chat_logger,
    get_tutorial_hint,
    get_all_screen_text,
    log_tutorial_hint,
)

# Import advanced autonomy features
try:
    from src.autonomy_features import (
        PrayerFlicker,
        PrayerType,
        SafeSpotDetector,
        QuizMasterHandler,
        FrogPrincessHandler,
        GoalBasedPlanner,
        Goal,
        GoalType,
        ResourceScanner,
        ObstacleDetector,
        LandmarkNavigator,
    )
    HAS_AUTONOMY_FEATURES = True
except ImportError as e:
    logger.warning(f"autonomy_features not available: {e}")
    HAS_AUTONOMY_FEATURES = False

# Import timing variance
try:
    from src.agent_tools import TimingVariance, TimingProfile
    HAS_TIMING_VARIANCE = True
except ImportError:
    HAS_TIMING_VARIANCE = False


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class AgentConfig:
    """Configuration for the autonomous agent."""
    # Timing
    tick_ms: int = 600  # OSRS game tick
    ticks_per_decision: int = 3  # Decide every N ticks (1.8s default)

    # Safety
    max_consecutive_failures: int = 5
    eat_at_hp_percent: float = 50.0
    flee_at_hp_percent: float = 20.0

    # Model
    model_name: str = "phi3:mini"
    max_tokens: int = 100

    # Behavior
    idle_check_enabled: bool = True
    random_event_check: bool = True
    auto_eat_enabled: bool = True

    # Advanced features (from autonomy_features.py)
    prayer_flicking_enabled: bool = False
    safe_spot_enabled: bool = True
    goal_planning_enabled: bool = True
    obstacle_detection_enabled: bool = True
    resource_scanning_enabled: bool = True

    # Timing variance (from agent_tools.py)
    timing_variance_enabled: bool = True
    timing_profile: str = "normal"  # normal, aggressive, cautious


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

SYSTEM_PROMPT = """You are an OSRS game agent. Output ONE command based on the game state.

Commands:
{commands}

Goal: {goal}

Output ONLY the command, nothing else. Examples:
- walk_dir north
- chop tree
- click npc
- wait 2
"""

def build_prompt(context: Dict[str, Any], goal: str) -> str:
    """Build the prompt for the model."""
    commands = "\n".join(f"  - {cmd}" for cmd in get_available_commands())

    system = SYSTEM_PROMPT.format(commands=commands, goal=goal)

    # Build context description
    parts = []

    if context.get("dialogue_active"):
        parts.append(f"DIALOGUE ACTIVE: {context.get('dialogue_text', '')[:100]}")
        if context.get("dialogue_options"):
            parts.append(f"Options: {context['dialogue_options']}")

    if context.get("random_event"):
        parts.append(f"RANDOM EVENT: {context['random_event']}")

    parts.append(f"Hover text: {context.get('hover_text', 'none')}")
    parts.append(f"Location: {context.get('location', 'unknown')}")
    parts.append(f"Health: {context.get('health_percent', 100):.0f}%")
    parts.append(f"Inventory full: {context.get('inventory_full', False)}")
    parts.append(f"In combat: {context.get('in_combat', False)}")

    state_desc = "\n".join(parts)

    return f"{system}\n\nCurrent state:\n{state_desc}\n\nYour command:"


# =============================================================================
# MAIN AGENT LOOP
# =============================================================================

class AutonomousAgent:
    """
    The main autonomous agent that ties everything together.

    Integrates:
    - snapshot_schema.py: Schema-compliant snapshots with fallback triggers
    - autonomy_features.py: Prayer flicking, safe spots, random event handlers
    - agent_tools.py: Timing variance for human-like behavior
    """

    def __init__(self, config: AgentConfig, goal: str):
        self.config = config
        self.goal = goal

        # Find game window
        self.window = None
        self.window_bounds = (0, 0, 800, 600)

        # Command executor
        self.commander: Optional[AgentCommander] = None

        # State tracking
        self.running = False
        self.tick_count = 0
        self.decision_count = 0
        self.consecutive_failures = 0
        self.last_command = ""
        self.command_history: List[str] = []

        # Advanced autonomy features (from autonomy_features.py)
        self.prayer_flicker: Optional[PrayerFlicker] = None
        self.safe_spot_detector: Optional[SafeSpotDetector] = None
        self.quiz_handler: Optional[QuizMasterHandler] = None
        self.frog_handler: Optional[FrogPrincessHandler] = None
        self.goal_planner: Optional[GoalBasedPlanner] = None
        self.resource_scanner: Optional[ResourceScanner] = None
        self.obstacle_detector: Optional[ObstacleDetector] = None
        self.landmark_navigator: Optional[LandmarkNavigator] = None

        # Timing variance (from agent_tools.py)
        self.timing_variance: Optional[TimingVariance] = None

        # Fallback trigger (from snapshot_schema.py)
        self.fallback_trigger = get_fallback_trigger()

        # Session tracking
        self.session_id = f"sess_{int(time.time())}"

    def setup(self) -> bool:
        """Initialize the agent."""
        print("=" * 60)
        print("AUTONOMOUS OSRS AGENT")
        print(f"Goal: {self.goal}")
        print(f"Session: {self.session_id}")
        print("=" * 60)

        # Find RuneLite window
        self.window = find_window('RuneLite')
        if not self.window:
            print("ERROR: RuneLite window not found")
            return False

        bounds = self.window.bounds
        self.window_bounds = (bounds[0], bounds[1], bounds[2], bounds[3])
        print(f"Found window: {bounds[2]-bounds[0]}x{bounds[3]-bounds[1]}")

        # Initialize commander
        self.commander = AgentCommander(
            window_bounds=self.window_bounds,
            snapshot_fn=self.capture_snapshot
        )

        # Initialize advanced autonomy features
        self._init_autonomy_features()

        # Initialize timing variance
        self._init_timing_variance()

        print(f"Features: schema={USE_SCHEMA_SNAPSHOT}, autonomy={HAS_AUTONOMY_FEATURES}, timing={HAS_TIMING_VARIANCE}")
        return True

    def _init_autonomy_features(self) -> None:
        """Initialize autonomy features from autonomy_features.py."""
        if not HAS_AUTONOMY_FEATURES:
            return

        try:
            if self.config.prayer_flicking_enabled:
                self.prayer_flicker = PrayerFlicker()

            if self.config.safe_spot_enabled:
                self.safe_spot_detector = SafeSpotDetector()

            # Always enable random event handlers
            self.quiz_handler = QuizMasterHandler()
            self.frog_handler = FrogPrincessHandler()

            if self.config.goal_planning_enabled:
                self.goal_planner = GoalBasedPlanner()

            if self.config.resource_scanning_enabled:
                self.resource_scanner = ResourceScanner()

            if self.config.obstacle_detection_enabled:
                self.obstacle_detector = ObstacleDetector()
                self.landmark_navigator = LandmarkNavigator()

            logger.info("Autonomy features initialized")
        except Exception as e:
            logger.warning(f"Failed to init autonomy features: {e}")

    def _init_timing_variance(self) -> None:
        """Initialize timing variance from agent_tools.py."""
        if not HAS_TIMING_VARIANCE or not self.config.timing_variance_enabled:
            return

        try:
            profile_map = {
                "normal": TimingProfile.NORMAL,
                "aggressive": TimingProfile.AGGRESSIVE,
                "cautious": TimingProfile.CAUTIOUS,
            }
            profile = profile_map.get(self.config.timing_profile, TimingProfile.NORMAL)
            self.timing_variance = TimingVariance(profile=profile)
            logger.info(f"Timing variance initialized: {self.config.timing_profile}")
        except Exception as e:
            logger.warning(f"Failed to init timing variance: {e}")

    def capture_snapshot(self) -> Dict[str, Any]:
        """Capture current game state using schema-compliant snapshot."""
        try:
            if USE_SCHEMA_SNAPSHOT:
                return capture_snapshot_v2(
                    window_bounds=self.window_bounds,
                    session_id=self.session_id,
                    force_ocr=False,
                )
            else:
                # Fallback to legacy snapshot
                from src.fast_perception import capture_snapshot
                return capture_snapshot(self.window_bounds)
        except Exception as e:
            logger.error(f"Snapshot error: {e}")
            return {}

    def get_model_decision(self, context: Dict[str, Any]) -> str:
        """Query local model for next action."""
        prompt = build_prompt(context, self.goal)

        try:
            response = run_local_model(prompt, timeout_s=15)

            # Clean up response - just get the command
            response = response.strip()
            # Take first line only
            if '\n' in response:
                response = response.split('\n')[0]

            return response

        except Exception as e:
            print(f"Model error: {e}")
            return "wait 1"

    def handle_priority_actions(self, snapshot: Dict[str, Any]) -> Optional[str]:
        """
        Handle priority actions that override normal decision making.
        Returns command if priority action needed, None otherwise.

        Priority order:
        1. Random events (quiz master, frog princess via autonomy_features.py)
        2. Death
        3. Critical health
        4. Prayer flicking (via autonomy_features.py)
        5. Dialogue
        """
        # Priority 1: Random events (enhanced with autonomy_features handlers)
        if self.config.random_event_check:
            # Check quiz master handler
            if self.quiz_handler and self.quiz_handler.detect_quiz_master(snapshot):
                ui = snapshot.get("ui", {})
                dialogue_options = ui.get("dialogue_options", [])
                if dialogue_options:
                    answer = self.quiz_handler.answer_question(
                        " ".join(dialogue_options),
                        dialogue_options
                    )
                    return f"option_key {answer}"

            # Check frog princess handler
            if self.frog_handler and self.frog_handler.detect_frog_event(snapshot):
                target = self.frog_handler.get_kiss_target(snapshot)
                if target:
                    return "talk_to Frog"

            # Fallback to standard random event detection
            event = detect_random_event(snapshot)
            if event:
                return f"handle_event {event}"

        # Priority 2: Death
        if detect_death(snapshot):
            return "wait 5"  # Wait for respawn

        # Priority 3: Critical health
        hp = get_health_percent(snapshot)
        if hp <= self.config.flee_at_hp_percent:
            return "flee"
        if hp <= self.config.eat_at_hp_percent and self.config.auto_eat_enabled:
            return "eat"

        # Priority 4: Prayer flicking (from autonomy_features.py)
        if self.prayer_flicker and self.prayer_flicker.should_flick():
            # Execute prayer flick
            self._execute_prayer_flick(snapshot)
            self.prayer_flicker.last_flick_time = time.time()
            # Don't return a command - flick was executed inline

        # Priority 5: Dialogue needs attention
        dialogue = detect_dialogue_state(snapshot)
        if dialogue.state != DialogueState.NONE:
            # Log the dialogue for tracking
            chat_logger = get_chat_logger()
            chat_logger.log_dialogue(dialogue)

            if dialogue.state == DialogueState.NPC_CHAT or dialogue.continue_available:
                return "continue_key"  # Use keyboard
            if dialogue.state == DialogueState.PLAYER_OPTIONS:
                return "option_key 1"  # Default to option 1

        # Also log tutorial hints
        hint = get_tutorial_hint(snapshot)
        if hint:
            log_tutorial_hint(snapshot)

        return None

    def _execute_prayer_flick(self, snapshot: Dict[str, Any]) -> None:
        """Execute a prayer flick using autonomy_features.py PrayerFlicker."""
        if not self.prayer_flicker:
            return

        from src.input_exec import move_mouse_path, click

        # Get prayer tab bounds from snapshot
        roi = snapshot.get("roi", {})
        prayer_tab = roi.get("prayer", {"x": 560, "y": 210, "width": 180, "height": 260})

        for prayer in self.prayer_flicker.active_prayers:
            pos = self.prayer_flicker.get_prayer_position(
                prayer,
                (prayer_tab["x"], prayer_tab["y"], prayer_tab["width"], prayer_tab["height"])
            )

            # Apply timing variance if available
            if self.timing_variance:
                delay = self.timing_variance.pre_action_delay()
                time.sleep(delay / 1000.0)

            # Click the prayer
            x, y = pos
            move_mouse_path(x, y, steps=3, curve_strength=0.05)
            click(button='left', dwell_ms=random.randint(30, 50))

            if self.timing_variance:
                delay = self.timing_variance.post_action_delay()
                time.sleep(delay / 1000.0)

    def execute_command(self, command: str) -> bool:
        """Execute a command and return success status."""
        cmd, args = parse_model_command(command)

        # Apply pre-action timing variance (from agent_tools.py)
        if self.timing_variance:
            delay = self.timing_variance.pre_action_delay()
            time.sleep(delay / 1000.0)

        if cmd == "handle_event":
            # Special handling for random events
            handle_random_event(args, self.window_bounds, self.capture_snapshot)
            return True

        result = self.commander.execute(cmd, args)

        # Apply post-action timing variance
        if self.timing_variance:
            delay = self.timing_variance.post_action_delay()
            time.sleep(delay / 1000.0)

        # Record success/failure for fallback trigger (from snapshot_schema.py)
        if self.fallback_trigger:
            if result.success:
                self.fallback_trigger.record_success()
            else:
                self.fallback_trigger.record_failure(result.message)

        if result.success:
            self.consecutive_failures = 0
            print(f"  [OK] {result.message}")
        else:
            self.consecutive_failures += 1
            print(f"  [FAIL] {result.message}")

        return result.success

    def tick(self) -> bool:
        """
        Execute one tick of the agent loop.
        Returns False if agent should stop.

        Note: Timing is handled by the run() loop, not here.
        This fixes the legacy double-sleep issue.
        """
        self.tick_count += 1

        # Only make decisions every N ticks
        # Note: Don't sleep here - run() handles tick timing
        if self.tick_count % self.config.ticks_per_decision != 0:
            return True

        self.decision_count += 1
        print(f"\n[Tick {self.tick_count}] Decision #{self.decision_count}")

        # Capture state
        snapshot = self.capture_snapshot()
        if not snapshot:
            print("  No snapshot available")
            return True

        # Check priority actions
        priority_cmd = self.handle_priority_actions(snapshot)
        if priority_cmd:
            print(f"  Priority: {priority_cmd}")
            self.execute_command(priority_cmd)
            return True

        # Get context for model
        context = get_context_for_model(snapshot)

        # Get model decision
        command = self.get_model_decision(context)
        print(f"  Model: {command}")

        # Track command
        self.last_command = command
        self.command_history.append(command)
        if len(self.command_history) > 100:
            self.command_history.pop(0)

        # Execute
        self.execute_command(command)

        # Check failure threshold
        if self.consecutive_failures >= self.config.max_consecutive_failures:
            print(f"\n[WARN] {self.consecutive_failures} consecutive failures - pausing")
            time.sleep(5)
            self.consecutive_failures = 0

        return True

    def run(self, max_ticks: int = 0) -> None:
        """
        Run the agent loop.

        Args:
            max_ticks: Maximum ticks to run (0 = infinite)
        """
        if not self.setup():
            return

        self.running = True
        print("\nStarting in 3 seconds...")
        time.sleep(3)

        try:
            while self.running:
                if max_ticks > 0 and self.tick_count >= max_ticks:
                    print(f"\nReached max ticks ({max_ticks})")
                    break

                if not self.tick():
                    break

                time.sleep(self.config.tick_ms / 1000.0)

        except KeyboardInterrupt:
            print("\n\nStopped by user")
        finally:
            self.running = False
            self.print_summary()

    def print_summary(self) -> None:
        """Print session summary."""
        print("\n" + "=" * 60)
        print("SESSION SUMMARY")
        print("=" * 60)
        print(f"Total ticks: {self.tick_count}")
        print(f"Decisions made: {self.decision_count}")
        print(f"Commands executed: {self.commander.command_count if self.commander else 0}")
        print(f"Last 10 commands: {self.command_history[-10:]}")


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Autonomous OSRS Agent")
    parser.add_argument("--goal", type=str, default="explore and learn",
                        help="Goal for the agent")
    parser.add_argument("--max-ticks", type=int, default=0,
                        help="Maximum ticks to run (0 = infinite)")
    parser.add_argument("--ticks-per-decision", type=int, default=3,
                        help="Ticks between decisions")
    parser.add_argument("--model", type=str, default="phi3:mini",
                        help="Local model to use")

    args = parser.parse_args()

    config = AgentConfig(
        ticks_per_decision=args.ticks_per_decision,
        model_name=args.model,
    )

    agent = AutonomousAgent(config, args.goal)
    agent.run(max_ticks=args.max_ticks)


if __name__ == "__main__":
    main()
