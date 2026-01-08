"""
Autonomous Agent - Complete integration of all systems.

This is the main agent loop that:
1. Captures game state (eyes)
2. Asks the local model for a decision (brain)
3. Executes the command (hands)
4. Validates and repeats

Usage:
    python -m src.autonomous_agent --goal "complete tutorial island"
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.perception import find_window
from src.fast_perception import capture_snapshot
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

    def setup(self) -> bool:
        """Initialize the agent."""
        print("=" * 60)
        print("AUTONOMOUS OSRS AGENT")
        print(f"Goal: {self.goal}")
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

        return True

    def capture_snapshot(self) -> Dict[str, Any]:
        """Capture current game state."""
        try:
            return capture_snapshot(self.window_bounds)
        except Exception as e:
            print(f"Snapshot error: {e}")
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
        """
        # Priority 1: Random events
        if self.config.random_event_check:
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

        # Priority 4: Dialogue needs attention
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

    def execute_command(self, command: str) -> bool:
        """Execute a command and return success status."""
        cmd, args = parse_model_command(command)

        if cmd == "handle_event":
            # Special handling for random events
            handle_random_event(args, self.window_bounds, self.capture_snapshot)
            return True

        result = self.commander.execute(cmd, args)

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
        """
        self.tick_count += 1

        # Only make decisions every N ticks
        if self.tick_count % self.config.ticks_per_decision != 0:
            time.sleep(self.config.tick_ms / 1000.0)
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
