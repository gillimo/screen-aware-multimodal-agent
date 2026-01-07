"""
State Machine Framework for Autonomous Agent Behavior.

Provides:
- Generic Phase class with entry/tick/exit lifecycle
- PhaseRegistry for activity-specific phases
- Goal-driven phase sequencing
- Phase transition detection from game state
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type
import time


# =============================================================================
# PHASE STATUS
# =============================================================================

class PhaseStatus(Enum):
    """Status of a phase execution"""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class PhaseResult:
    """Result of a phase tick"""
    status: PhaseStatus
    next_phase: Optional[str] = None  # Name of phase to transition to
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# BASE PHASE CLASS
# =============================================================================

class Phase(ABC):
    """
    Base class for all phases.

    A phase represents a distinct state of agent behavior.
    Examples: "talk_to_npc", "walk_to_location", "fish_at_spot"

    Lifecycle:
    1. on_enter() - Called once when entering the phase
    2. tick() - Called repeatedly while phase is active
    3. on_exit() - Called once when leaving the phase
    """

    def __init__(self, name: str):
        self.name = name
        self.status = PhaseStatus.NOT_STARTED
        self.tick_count = 0
        self.start_time: Optional[float] = None
        self.context: Dict[str, Any] = {}

    def on_enter(self, context: Dict[str, Any]) -> None:
        """
        Called when entering this phase.
        Override to perform setup actions.
        """
        self.context = context
        self.status = PhaseStatus.RUNNING
        self.tick_count = 0
        self.start_time = time.time()

    @abstractmethod
    def tick(
        self,
        snapshot: Dict[str, Any],
        context: Dict[str, Any],
    ) -> PhaseResult:
        """
        Execute one tick of this phase.

        Args:
            snapshot: Current game state snapshot
            context: Shared context (goals, inventory, etc.)

        Returns:
            PhaseResult indicating status and potential transition
        """
        pass

    def on_exit(self, context: Dict[str, Any]) -> None:
        """
        Called when leaving this phase.
        Override to perform cleanup.
        """
        pass

    def elapsed_seconds(self) -> float:
        """Time spent in this phase"""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time


# =============================================================================
# COMMON PHASE IMPLEMENTATIONS
# =============================================================================

class WaitPhase(Phase):
    """Wait for a condition or timeout."""

    def __init__(
        self,
        name: str,
        condition_fn: Optional[Callable[[Dict], bool]] = None,
        timeout_seconds: float = 10.0,
        next_phase: str = "",
    ):
        super().__init__(name)
        self.condition_fn = condition_fn
        self.timeout_seconds = timeout_seconds
        self.next_phase_name = next_phase

    def tick(self, snapshot: Dict[str, Any], context: Dict[str, Any]) -> PhaseResult:
        self.tick_count += 1

        # Check condition
        if self.condition_fn and self.condition_fn(snapshot):
            return PhaseResult(
                status=PhaseStatus.COMPLETED,
                next_phase=self.next_phase_name,
                message="Condition met"
            )

        # Check timeout
        if self.elapsed_seconds() > self.timeout_seconds:
            return PhaseResult(
                status=PhaseStatus.FAILED,
                message=f"Timeout after {self.timeout_seconds}s"
            )

        return PhaseResult(status=PhaseStatus.RUNNING)


class DialoguePhase(Phase):
    """Handle NPC dialogue interaction."""

    def __init__(
        self,
        name: str,
        expected_options: Optional[List[str]] = None,
        select_option: Optional[str] = None,
        next_phase: str = "",
    ):
        super().__init__(name)
        self.expected_options = expected_options or []
        self.select_option = select_option
        self.next_phase_name = next_phase

    def tick(self, snapshot: Dict[str, Any], context: Dict[str, Any]) -> PhaseResult:
        from src.game_actions import (
            detect_dialogue_state,
            DialogueState,
            click_dialogue_continue,
            select_dialogue_by_text,
        )

        self.tick_count += 1
        window_bounds = context.get("window_bounds", (0, 0, 800, 600))

        dialogue = detect_dialogue_state(snapshot)

        if dialogue.state == DialogueState.NONE:
            # No dialogue - might be waiting or done
            if self.tick_count > 20:
                return PhaseResult(
                    status=PhaseStatus.COMPLETED,
                    next_phase=self.next_phase_name,
                    message="Dialogue ended"
                )
            return PhaseResult(status=PhaseStatus.RUNNING)

        if dialogue.state == DialogueState.NPC_CHAT:
            # NPC is talking, click to continue
            if dialogue.continue_available:
                click_dialogue_continue(snapshot, window_bounds)
            return PhaseResult(status=PhaseStatus.RUNNING, message="Continuing dialogue")

        if dialogue.state == DialogueState.PLAYER_OPTIONS:
            # Player needs to select an option
            if self.select_option:
                result = select_dialogue_by_text(
                    self.select_option,
                    snapshot,
                    window_bounds
                )
                if result.success:
                    return PhaseResult(
                        status=PhaseStatus.RUNNING,
                        message=f"Selected: {self.select_option}"
                    )
            return PhaseResult(
                status=PhaseStatus.BLOCKED,
                message="Waiting for option selection"
            )

        return PhaseResult(status=PhaseStatus.RUNNING)


class InteractPhase(Phase):
    """Interact with an NPC or object."""

    def __init__(
        self,
        name: str,
        target: str,
        action: str = "",
        is_npc: bool = True,
        next_phase: str = "",
    ):
        super().__init__(name)
        self.target = target
        self.action = action
        self.is_npc = is_npc
        self.next_phase_name = next_phase
        self.interaction_attempted = False

    def tick(self, snapshot: Dict[str, Any], context: Dict[str, Any]) -> PhaseResult:
        from src.game_actions import interact_with_npc, interact_with_object

        self.tick_count += 1
        window_bounds = context.get("window_bounds", (0, 0, 800, 600))
        snapshot_fn = context.get("snapshot_fn", lambda: snapshot)

        if self.interaction_attempted:
            # Already tried, check if successful
            return PhaseResult(
                status=PhaseStatus.COMPLETED,
                next_phase=self.next_phase_name,
                message="Interaction completed"
            )

        # Attempt interaction
        if self.is_npc:
            result = interact_with_npc(
                self.target,
                self.action,
                window_bounds,
                snapshot_fn
            )
        else:
            result = interact_with_object(
                self.target,
                self.action,
                window_bounds,
                snapshot_fn
            )

        self.interaction_attempted = True

        if result.success:
            return PhaseResult(
                status=PhaseStatus.RUNNING,
                message=f"Interacted with {self.target}"
            )
        else:
            return PhaseResult(
                status=PhaseStatus.FAILED,
                message=f"Failed to interact: {result.failure_reason}"
            )


class WalkPhase(Phase):
    """Walk to a location using minimap or game view."""

    def __init__(
        self,
        name: str,
        target_text: Optional[str] = None,
        minimap_offset: Optional[tuple] = None,
        next_phase: str = "",
    ):
        super().__init__(name)
        self.target_text = target_text
        self.minimap_offset = minimap_offset
        self.next_phase_name = next_phase
        self.walk_initiated = False

    def tick(self, snapshot: Dict[str, Any], context: Dict[str, Any]) -> PhaseResult:
        from src.game_actions import click_minimap, search_and_click

        self.tick_count += 1
        window_bounds = context.get("window_bounds", (0, 0, 800, 600))
        snapshot_fn = context.get("snapshot_fn", lambda: snapshot)

        if self.walk_initiated:
            # Wait for arrival (simple tick-based wait for now)
            if self.tick_count > 10:
                return PhaseResult(
                    status=PhaseStatus.COMPLETED,
                    next_phase=self.next_phase_name,
                    message="Walk completed"
                )
            return PhaseResult(status=PhaseStatus.RUNNING, message="Walking...")

        if self.minimap_offset:
            dx, dy = self.minimap_offset
            click_minimap(dx, dy, window_bounds, snapshot)
            self.walk_initiated = True
            return PhaseResult(status=PhaseStatus.RUNNING, message="Walking to minimap point")

        if self.target_text:
            result = search_and_click(self.target_text, window_bounds, snapshot_fn)
            self.walk_initiated = True
            if result.success:
                return PhaseResult(status=PhaseStatus.RUNNING, message=f"Walking to {self.target_text}")
            else:
                return PhaseResult(status=PhaseStatus.FAILED, message="Target not found")

        return PhaseResult(status=PhaseStatus.FAILED, message="No walk target specified")


# =============================================================================
# PHASE REGISTRY
# =============================================================================

class PhaseRegistry:
    """
    Registry of available phases for an activity.

    Example usage:
        registry = PhaseRegistry()
        registry.register("talk_to_guide", DialoguePhase("talk_to_guide"))
        registry.register("walk_to_tree", WalkPhase("walk_to_tree"))
    """

    def __init__(self):
        self._phases: Dict[str, Phase] = {}
        self._factories: Dict[str, Callable[[], Phase]] = {}

    def register(self, name: str, phase: Phase) -> None:
        """Register a phase instance."""
        self._phases[name] = phase

    def register_factory(self, name: str, factory: Callable[[], Phase]) -> None:
        """Register a phase factory for lazy instantiation."""
        self._factories[name] = factory

    def get(self, name: str) -> Optional[Phase]:
        """Get a phase by name."""
        if name in self._phases:
            return self._phases[name]
        if name in self._factories:
            phase = self._factories[name]()
            self._phases[name] = phase
            return phase
        return None

    def list_phases(self) -> List[str]:
        """List all registered phase names."""
        return list(set(self._phases.keys()) | set(self._factories.keys()))


# =============================================================================
# STATE MACHINE CONTROLLER
# =============================================================================

@dataclass
class Goal:
    """A goal the agent is trying to achieve."""
    name: str
    description: str = ""
    phases: List[str] = field(default_factory=list)  # Ordered phase sequence
    completed: bool = False
    priority: int = 0


class StateMachine:
    """
    Main state machine controller.

    Manages phase transitions and goal progress.
    """

    def __init__(self, registry: PhaseRegistry):
        self.registry = registry
        self.current_phase: Optional[Phase] = None
        self.current_goal: Optional[Goal] = None
        self.phase_history: List[str] = []
        self.context: Dict[str, Any] = {}
        self.goals: List[Goal] = []

    def set_goal(self, goal: Goal) -> None:
        """Set a new goal to work towards."""
        self.current_goal = goal
        if goal.phases:
            first_phase = goal.phases[0]
            self.transition_to(first_phase)

    def add_goal(self, goal: Goal) -> None:
        """Add a goal to the queue."""
        self.goals.append(goal)
        self.goals.sort(key=lambda g: -g.priority)  # Higher priority first

    def transition_to(self, phase_name: str) -> bool:
        """Transition to a new phase."""
        # Exit current phase
        if self.current_phase:
            self.current_phase.on_exit(self.context)
            self.phase_history.append(self.current_phase.name)

        # Enter new phase
        new_phase = self.registry.get(phase_name)
        if new_phase is None:
            return False

        self.current_phase = new_phase
        self.current_phase.on_enter(self.context)
        return True

    def tick(self, snapshot: Dict[str, Any]) -> PhaseResult:
        """
        Execute one tick of the state machine.

        Returns the result of the current phase's tick.
        """
        if self.current_phase is None:
            # No active phase - try to start next goal
            if self.goals and not self.current_goal:
                self.set_goal(self.goals.pop(0))

            if self.current_phase is None:
                return PhaseResult(
                    status=PhaseStatus.NOT_STARTED,
                    message="No active phase"
                )

        # Update context with snapshot
        self.context["snapshot"] = snapshot

        # Run current phase tick
        result = self.current_phase.tick(snapshot, self.context)

        # Handle phase completion/transition
        if result.status == PhaseStatus.COMPLETED:
            if result.next_phase:
                self.transition_to(result.next_phase)
            elif self.current_goal and self.current_goal.phases:
                # Move to next phase in goal
                current_idx = -1
                try:
                    current_idx = self.current_goal.phases.index(self.current_phase.name)
                except ValueError:
                    pass

                if current_idx >= 0 and current_idx < len(self.current_goal.phases) - 1:
                    next_phase = self.current_goal.phases[current_idx + 1]
                    self.transition_to(next_phase)
                else:
                    # Goal completed
                    self.current_goal.completed = True
                    self.current_phase = None
                    if self.goals:
                        self.set_goal(self.goals.pop(0))

        elif result.status == PhaseStatus.FAILED:
            # Handle failure - could retry, skip, or escalate
            self.current_phase = None

        return result

    def get_status(self) -> Dict[str, Any]:
        """Get current state machine status."""
        return {
            "current_phase": self.current_phase.name if self.current_phase else None,
            "phase_status": self.current_phase.status.value if self.current_phase else None,
            "current_goal": self.current_goal.name if self.current_goal else None,
            "goal_completed": self.current_goal.completed if self.current_goal else None,
            "pending_goals": len(self.goals),
            "phase_history": self.phase_history[-10:],  # Last 10 phases
        }


# =============================================================================
# TUTORIAL ISLAND PHASES (EXAMPLE)
# =============================================================================

def create_tutorial_island_registry() -> PhaseRegistry:
    """
    Create phase registry for Tutorial Island.

    This is an example of how to set up phases for a specific activity.
    """
    registry = PhaseRegistry()

    # Gielinor Guide phase
    registry.register("talk_to_guide", InteractPhase(
        name="talk_to_guide",
        target="Gielinor Guide",
        action="Talk-to",
        is_npc=True,
        next_phase="guide_dialogue"
    ))

    registry.register("guide_dialogue", DialoguePhase(
        name="guide_dialogue",
        next_phase="open_settings"
    ))

    # Survival Expert phase
    registry.register("exit_guide_building", WalkPhase(
        name="exit_guide_building",
        target_text="Door",
        next_phase="find_survival_expert"
    ))

    registry.register("find_survival_expert", InteractPhase(
        name="find_survival_expert",
        target="Survival Expert",
        action="Talk-to",
        is_npc=True,
        next_phase="survival_dialogue"
    ))

    registry.register("survival_dialogue", DialoguePhase(
        name="survival_dialogue",
        next_phase="get_items"
    ))

    # Add more phases as needed...

    return registry


def create_tutorial_island_goal() -> Goal:
    """Create goal for completing Tutorial Island."""
    return Goal(
        name="complete_tutorial_island",
        description="Complete Tutorial Island and arrive on mainland",
        phases=[
            "talk_to_guide",
            "guide_dialogue",
            "exit_guide_building",
            "find_survival_expert",
            "survival_dialogue",
            # ... more phases
        ],
        priority=100
    )
