"""
Tutorial Island Phase Implementations

This module implements:
- T17: Gielinor Guide phase
- T18: Survival Expert phase
- T19: Master Chef phase
- T20: Quest Guide phase
- T21: Mining Instructor phase
- T22: Combat Instructor phase
- T23: Financial Advisor phase
- T24: Brother Brace phase
- T25: Magic Instructor phase
- T26: Phase detection from tutorial hint OCR
- T27: Phase transition verification

Nightfall - 2026-01-07
"""
from __future__ import annotations

import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# TUTORIAL PHASE ENUM
# =============================================================================

class TutorialPhase(Enum):
    """Tutorial Island phases in order."""
    CHARACTER_CREATION = "character_creation"
    GIELINOR_GUIDE = "gielinor_guide"
    SURVIVAL_EXPERT = "survival_expert"
    MASTER_CHEF = "master_chef"
    QUEST_GUIDE = "quest_guide"
    MINING_INSTRUCTOR = "mining_instructor"
    COMBAT_INSTRUCTOR = "combat_instructor"
    FINANCIAL_ADVISOR = "financial_advisor"
    BROTHER_BRACE = "brother_brace"
    MAGIC_INSTRUCTOR = "magic_instructor"
    LEAVING_ISLAND = "leaving_island"
    COMPLETE = "complete"


# =============================================================================
# PHASE DETECTION (T26)
# =============================================================================

# Keywords in tutorial hints that indicate each phase
PHASE_KEYWORDS = {
    TutorialPhase.GIELINOR_GUIDE: [
        "gielinor guide", "getting started", "talk to the gielinor guide",
        "character", "experience", "options", "settings",
    ],
    TutorialPhase.SURVIVAL_EXPERT: [
        "survival expert", "fishing", "fire", "cooking",
        "shrimp", "logs", "tinderbox", "raw shrimps",
        "light a fire", "cook", "net",
    ],
    TutorialPhase.MASTER_CHEF: [
        "master chef", "bread", "flour", "dough",
        "range", "cooking range", "bucket of water",
        "pot of flour", "mix", "bake",
    ],
    TutorialPhase.QUEST_GUIDE: [
        "quest guide", "quest", "journal", "quest tab",
        "quest list", "tracker",
    ],
    TutorialPhase.MINING_INSTRUCTOR: [
        "mining instructor", "mining", "smithing",
        "pickaxe", "tin", "copper", "ore", "furnace",
        "anvil", "bronze", "smelt", "dagger",
    ],
    TutorialPhase.COMBAT_INSTRUCTOR: [
        "combat instructor", "combat", "attack", "rat",
        "melee", "sword", "shield", "equipped",
        "strength", "defence", "rat", "giant rat",
    ],
    TutorialPhase.FINANCIAL_ADVISOR: [
        "financial advisor", "bank", "money", "coins",
        "deposit", "withdraw", "poll booth",
    ],
    TutorialPhase.BROTHER_BRACE: [
        "brother brace", "prayer", "friends", "ignore",
        "chapel", "altar", "bury", "bones",
    ],
    TutorialPhase.MAGIC_INSTRUCTOR: [
        "magic instructor", "magic", "rune", "spell",
        "chicken", "wind strike", "air rune", "mind rune",
        "cast", "mainland",
    ],
    TutorialPhase.LEAVING_ISLAND: [
        "mainland", "leave", "portal", "ready",
        "adventure", "world",
    ],
}

# Varbit 281 progress values for each phase
VARBIT_PROGRESS = {
    0: TutorialPhase.CHARACTER_CREATION,
    10: TutorialPhase.GIELINOR_GUIDE,
    20: TutorialPhase.SURVIVAL_EXPERT,
    70: TutorialPhase.MASTER_CHEF,
    120: TutorialPhase.QUEST_GUIDE,
    170: TutorialPhase.MINING_INSTRUCTOR,
    300: TutorialPhase.COMBAT_INSTRUCTOR,
    510: TutorialPhase.FINANCIAL_ADVISOR,
    525: TutorialPhase.BROTHER_BRACE,
    610: TutorialPhase.MAGIC_INSTRUCTOR,
    1000: TutorialPhase.COMPLETE,
}


def detect_phase_from_hint(hint_text: str) -> Optional[TutorialPhase]:
    """
    Detect tutorial phase from hint text (T26).

    Args:
        hint_text: The tutorial hint text from OCR

    Returns:
        Detected phase or None if unknown
    """
    if not hint_text:
        return None

    hint_lower = hint_text.lower()

    # Check each phase's keywords
    for phase, keywords in PHASE_KEYWORDS.items():
        if any(kw in hint_lower for kw in keywords):
            return phase

    return None


def detect_phase_from_varbit(varbit_value: int) -> TutorialPhase:
    """
    Detect tutorial phase from varbit 281 progress value.

    Args:
        varbit_value: The current varbit 281 value

    Returns:
        Current tutorial phase
    """
    # Find the highest varbit value that's <= current progress
    current_phase = TutorialPhase.CHARACTER_CREATION

    for threshold, phase in sorted(VARBIT_PROGRESS.items()):
        if varbit_value >= threshold:
            current_phase = phase
        else:
            break

    return current_phase


def detect_phase(snapshot: Dict[str, Any]) -> TutorialPhase:
    """
    Detect current tutorial phase from snapshot.

    Uses multiple signals:
    1. Varbit 281 progress (most reliable)
    2. Tutorial hint text
    3. NPC detection

    Returns:
        Current tutorial phase
    """
    # Try varbit first (most reliable)
    runelite = snapshot.get("runelite_data", {})
    tutorial_progress = runelite.get("tutorial_progress", 0)

    if tutorial_progress > 0:
        return detect_phase_from_varbit(tutorial_progress)

    # Fall back to hint detection
    ocr = snapshot.get("ocr", [])
    for entry in ocr:
        if isinstance(entry, dict) and entry.get("region") == "tutorial_hint":
            hint = entry.get("text", "")
            phase = detect_phase_from_hint(hint)
            if phase:
                return phase

    # Check for NPCs as fallback
    npcs = runelite.get("npcs_on_screen", [])
    npc_names = [npc.get("name", "").lower() for npc in npcs]

    if "gielinor guide" in npc_names:
        return TutorialPhase.GIELINOR_GUIDE
    if "survival expert" in npc_names:
        return TutorialPhase.SURVIVAL_EXPERT
    if "master chef" in npc_names:
        return TutorialPhase.MASTER_CHEF
    if "quest guide" in npc_names:
        return TutorialPhase.QUEST_GUIDE
    if "mining instructor" in npc_names:
        return TutorialPhase.MINING_INSTRUCTOR
    if "combat instructor" in npc_names:
        return TutorialPhase.COMBAT_INSTRUCTOR
    if "financial advisor" in npc_names:
        return TutorialPhase.FINANCIAL_ADVISOR
    if "brother brace" in npc_names:
        return TutorialPhase.BROTHER_BRACE
    if "magic instructor" in npc_names:
        return TutorialPhase.MAGIC_INSTRUCTOR

    return TutorialPhase.CHARACTER_CREATION


# =============================================================================
# PHASE TRANSITION VERIFICATION (T27)
# =============================================================================

@dataclass
class PhaseTransition:
    """Record of a phase transition."""
    from_phase: TutorialPhase
    to_phase: TutorialPhase
    timestamp: float
    verified: bool = False
    varbit_before: int = 0
    varbit_after: int = 0


class PhaseVerifier:
    """
    Verifies tutorial phase transitions (T27).

    Tracks phase changes and ensures they're valid.
    """

    def __init__(self):
        self.current_phase: TutorialPhase = TutorialPhase.CHARACTER_CREATION
        self.transitions: List[PhaseTransition] = []
        self.last_varbit: int = 0

    def update(self, snapshot: Dict[str, Any]) -> Optional[PhaseTransition]:
        """
        Update state from snapshot and detect transitions.

        Returns:
            PhaseTransition if a transition occurred, None otherwise
        """
        detected_phase = detect_phase(snapshot)
        runelite = snapshot.get("runelite_data", {})
        current_varbit = runelite.get("tutorial_progress", 0)

        if detected_phase != self.current_phase:
            # Verify transition is valid
            valid = self._is_valid_transition(self.current_phase, detected_phase)

            transition = PhaseTransition(
                from_phase=self.current_phase,
                to_phase=detected_phase,
                timestamp=time.time(),
                verified=valid,
                varbit_before=self.last_varbit,
                varbit_after=current_varbit,
            )

            self.transitions.append(transition)
            self.current_phase = detected_phase
            self.last_varbit = current_varbit

            if valid:
                logger.info(f"Phase transition: {transition.from_phase.value} -> {transition.to_phase.value}")
            else:
                logger.warning(f"Unexpected phase transition: {transition.from_phase.value} -> {transition.to_phase.value}")

            return transition

        self.last_varbit = current_varbit
        return None

    def _is_valid_transition(
        self,
        from_phase: TutorialPhase,
        to_phase: TutorialPhase,
    ) -> bool:
        """Check if a phase transition is valid (in correct order)."""
        phase_order = list(TutorialPhase)

        try:
            from_idx = phase_order.index(from_phase)
            to_idx = phase_order.index(to_phase)

            # Valid if moving forward or staying in place
            return to_idx >= from_idx
        except ValueError:
            return False

    def get_phase_progress(self) -> float:
        """Get overall progress through tutorial (0.0 to 1.0)."""
        phase_order = list(TutorialPhase)
        current_idx = phase_order.index(self.current_phase)
        total_phases = len(phase_order) - 1  # Exclude COMPLETE

        return current_idx / total_phases


# =============================================================================
# BASE PHASE HANDLER
# =============================================================================

@dataclass
class PhaseAction:
    """An action to perform in a tutorial phase."""
    action_type: str  # "talk_to", "click_object", "use_item", etc.
    target: str       # NPC name, object name, item name
    details: Dict[str, Any] = field(default_factory=dict)
    completed: bool = False


class PhaseHandler(ABC):
    """
    Base class for tutorial phase handlers.

    Each phase handler implements the logic for completing
    a specific section of Tutorial Island.
    """

    def __init__(self):
        self.phase: TutorialPhase = TutorialPhase.CHARACTER_CREATION
        self.actions: List[PhaseAction] = []
        self.current_action_idx: int = 0
        self.completed: bool = False

    @abstractmethod
    def get_phase(self) -> TutorialPhase:
        """Get the phase this handler manages."""
        pass

    @abstractmethod
    def initialize(self, snapshot: Dict[str, Any]):
        """Initialize the phase handler with current state."""
        pass

    @abstractmethod
    def get_next_action(self, snapshot: Dict[str, Any]) -> Optional[PhaseAction]:
        """Get the next action to perform."""
        pass

    @abstractmethod
    def is_complete(self, snapshot: Dict[str, Any]) -> bool:
        """Check if this phase is complete."""
        pass

    def mark_action_complete(self, action: PhaseAction):
        """Mark an action as completed."""
        action.completed = True
        self.current_action_idx += 1


# =============================================================================
# T17: GIELINOR GUIDE PHASE
# =============================================================================

class GielinorGuidePhase(PhaseHandler):
    """
    Handles the Gielinor Guide (starting) phase (T17).

    Steps:
    1. Talk to Gielinor Guide
    2. Open Options menu
    3. Talk to Gielinor Guide again
    4. Walk through door to Survival Expert area
    """

    def get_phase(self) -> TutorialPhase:
        return TutorialPhase.GIELINOR_GUIDE

    def initialize(self, snapshot: Dict[str, Any]):
        self.actions = [
            PhaseAction("talk_to", "Gielinor Guide", {"dialogue_option": 1}),
            PhaseAction("open_tab", "options", {}),
            PhaseAction("talk_to", "Gielinor Guide", {"dialogue_option": 1}),
            PhaseAction("click_object", "Door", {"action": "open"}),
        ]

    def get_next_action(self, snapshot: Dict[str, Any]) -> Optional[PhaseAction]:
        if self.current_action_idx >= len(self.actions):
            return None

        action = self.actions[self.current_action_idx]

        # Check if current action is already done based on game state
        runelite = snapshot.get("runelite_data", {})
        progress = runelite.get("tutorial_progress", 0)

        # Adjust action based on progress
        if action.action_type == "open_tab" and progress >= 7:
            # Options tab already opened
            action.completed = True
            self.current_action_idx += 1
            return self.get_next_action(snapshot)

        return action

    def is_complete(self, snapshot: Dict[str, Any]) -> bool:
        runelite = snapshot.get("runelite_data", {})
        progress = runelite.get("tutorial_progress", 0)
        return progress >= 20  # Moving to Survival Expert


# =============================================================================
# T18: SURVIVAL EXPERT PHASE
# =============================================================================

class SurvivalExpertPhase(PhaseHandler):
    """
    Handles the Survival Expert phase (T18).

    Steps:
    1. Talk to Survival Expert
    2. Open inventory tab
    3. Fish shrimp (multiple)
    4. Open skills tab
    5. Talk to Survival Expert
    6. Chop tree for logs
    7. Light fire
    8. Cook shrimp
    9. Walk to next area
    """

    def get_phase(self) -> TutorialPhase:
        return TutorialPhase.SURVIVAL_EXPERT

    def initialize(self, snapshot: Dict[str, Any]):
        self.actions = [
            PhaseAction("talk_to", "Survival Expert", {}),
            PhaseAction("open_tab", "inventory", {}),
            PhaseAction("click_object", "Fishing spot", {"action": "net"}),
            PhaseAction("wait", "", {"condition": "inventory_has", "item": "raw shrimps"}),
            PhaseAction("open_tab", "skills", {}),
            PhaseAction("talk_to", "Survival Expert", {}),
            PhaseAction("click_object", "Tree", {"action": "chop down"}),
            PhaseAction("wait", "", {"condition": "inventory_has", "item": "logs"}),
            PhaseAction("use_item", "Tinderbox", {"target_item": "Logs"}),
            PhaseAction("wait", "", {"condition": "fire_lit"}),
            PhaseAction("use_item", "Raw shrimps", {"target_object": "Fire"}),
            PhaseAction("wait", "", {"condition": "inventory_has", "item": "shrimps"}),
            PhaseAction("click_object", "Gate", {"action": "open"}),
        ]

    def get_next_action(self, snapshot: Dict[str, Any]) -> Optional[PhaseAction]:
        if self.current_action_idx >= len(self.actions):
            return None

        action = self.actions[self.current_action_idx]

        # Check inventory for progress
        runelite = snapshot.get("runelite_data", {})
        inventory_count = runelite.get("inventory_count", 0)

        # Handle wait conditions
        if action.action_type == "wait":
            condition = action.details.get("condition")
            if condition == "inventory_has":
                # Check if item in inventory
                # This would need inventory content check
                pass

        return action

    def is_complete(self, snapshot: Dict[str, Any]) -> bool:
        runelite = snapshot.get("runelite_data", {})
        progress = runelite.get("tutorial_progress", 0)
        return progress >= 70  # Moving to Master Chef


# =============================================================================
# T19: MASTER CHEF PHASE
# =============================================================================

class MasterChefPhase(PhaseHandler):
    """
    Handles the Master Chef phase (T19).

    Steps:
    1. Talk to Master Chef
    2. Make bread dough (flour + water)
    3. Cook bread on range
    4. Walk to next area
    """

    def get_phase(self) -> TutorialPhase:
        return TutorialPhase.MASTER_CHEF

    def initialize(self, snapshot: Dict[str, Any]):
        self.actions = [
            PhaseAction("talk_to", "Master Chef", {}),
            PhaseAction("use_item", "Pot of flour", {"target_item": "Bucket of water"}),
            PhaseAction("use_item", "Bread dough", {"target_object": "Range"}),
            PhaseAction("wait", "", {"condition": "inventory_has", "item": "bread"}),
            PhaseAction("walk_to", "Music tab door", {}),
            PhaseAction("click_object", "Door", {"action": "open"}),
        ]

    def get_next_action(self, snapshot: Dict[str, Any]) -> Optional[PhaseAction]:
        if self.current_action_idx >= len(self.actions):
            return None
        return self.actions[self.current_action_idx]

    def is_complete(self, snapshot: Dict[str, Any]) -> bool:
        runelite = snapshot.get("runelite_data", {})
        progress = runelite.get("tutorial_progress", 0)
        return progress >= 120


# =============================================================================
# T20: QUEST GUIDE PHASE
# =============================================================================

class QuestGuidePhase(PhaseHandler):
    """
    Handles the Quest Guide phase (T20).

    Steps:
    1. Talk to Quest Guide
    2. Open quest tab
    3. Talk to Quest Guide again
    4. Walk to mining area
    """

    def get_phase(self) -> TutorialPhase:
        return TutorialPhase.QUEST_GUIDE

    def initialize(self, snapshot: Dict[str, Any]):
        self.actions = [
            PhaseAction("talk_to", "Quest Guide", {}),
            PhaseAction("open_tab", "quest", {}),
            PhaseAction("talk_to", "Quest Guide", {}),
            PhaseAction("click_object", "Ladder", {"action": "climb-down"}),
        ]

    def get_next_action(self, snapshot: Dict[str, Any]) -> Optional[PhaseAction]:
        if self.current_action_idx >= len(self.actions):
            return None
        return self.actions[self.current_action_idx]

    def is_complete(self, snapshot: Dict[str, Any]) -> bool:
        runelite = snapshot.get("runelite_data", {})
        progress = runelite.get("tutorial_progress", 0)
        return progress >= 170


# =============================================================================
# T21: MINING INSTRUCTOR PHASE
# =============================================================================

class MiningInstructorPhase(PhaseHandler):
    """
    Handles the Mining Instructor phase (T21).

    Steps:
    1. Talk to Mining Instructor
    2. Mine tin ore
    3. Mine copper ore
    4. Smelt bronze bar at furnace
    5. Talk to Mining Instructor
    6. Smith bronze dagger at anvil
    7. Walk to next area
    """

    def get_phase(self) -> TutorialPhase:
        return TutorialPhase.MINING_INSTRUCTOR

    def initialize(self, snapshot: Dict[str, Any]):
        self.actions = [
            PhaseAction("talk_to", "Mining Instructor", {}),
            PhaseAction("click_object", "Tin rocks", {"action": "mine"}),
            PhaseAction("wait", "", {"condition": "inventory_has", "item": "tin ore"}),
            PhaseAction("click_object", "Copper rocks", {"action": "mine"}),
            PhaseAction("wait", "", {"condition": "inventory_has", "item": "copper ore"}),
            PhaseAction("click_object", "Furnace", {"action": "smelt"}),
            PhaseAction("wait", "", {"condition": "inventory_has", "item": "bronze bar"}),
            PhaseAction("talk_to", "Mining Instructor", {}),
            PhaseAction("click_object", "Anvil", {"action": "smith"}),
            PhaseAction("click_interface", "Bronze dagger", {}),
            PhaseAction("wait", "", {"condition": "inventory_has", "item": "bronze dagger"}),
            PhaseAction("click_object", "Gate", {"action": "open"}),
        ]

    def get_next_action(self, snapshot: Dict[str, Any]) -> Optional[PhaseAction]:
        if self.current_action_idx >= len(self.actions):
            return None
        return self.actions[self.current_action_idx]

    def is_complete(self, snapshot: Dict[str, Any]) -> bool:
        runelite = snapshot.get("runelite_data", {})
        progress = runelite.get("tutorial_progress", 0)
        return progress >= 300


# =============================================================================
# T22: COMBAT INSTRUCTOR PHASE
# =============================================================================

class CombatInstructorPhase(PhaseHandler):
    """
    Handles the Combat Instructor phase (T22).

    Steps:
    1. Talk to Combat Instructor
    2. Open equipment tab
    3. View equipment stats
    4. Equip bronze dagger
    5. Talk to Combat Instructor
    6. Equip sword and shield
    7. Open combat tab
    8. Attack rat with melee
    9. Talk to Combat Instructor
    10. Equip bow and arrows
    11. Attack rat with ranged
    12. Walk to next area
    """

    def get_phase(self) -> TutorialPhase:
        return TutorialPhase.COMBAT_INSTRUCTOR

    def initialize(self, snapshot: Dict[str, Any]):
        self.actions = [
            PhaseAction("talk_to", "Combat Instructor", {}),
            PhaseAction("open_tab", "equipment", {}),
            PhaseAction("click_interface", "Equipment stats", {}),
            PhaseAction("equip", "Bronze dagger", {}),
            PhaseAction("talk_to", "Combat Instructor", {}),
            PhaseAction("equip", "Bronze sword", {}),
            PhaseAction("equip", "Wooden shield", {}),
            PhaseAction("open_tab", "combat", {}),
            PhaseAction("click_object", "Gate", {"action": "open"}),
            PhaseAction("attack", "Giant rat", {}),
            PhaseAction("wait", "", {"condition": "combat_complete"}),
            PhaseAction("click_object", "Gate", {"action": "open"}),
            PhaseAction("talk_to", "Combat Instructor", {}),
            PhaseAction("equip", "Shortbow", {}),
            PhaseAction("equip", "Bronze arrow", {}),
            PhaseAction("attack", "Giant rat", {}),
            PhaseAction("wait", "", {"condition": "combat_complete"}),
            PhaseAction("click_object", "Ladder", {"action": "climb-up"}),
        ]

    def get_next_action(self, snapshot: Dict[str, Any]) -> Optional[PhaseAction]:
        if self.current_action_idx >= len(self.actions):
            return None
        return self.actions[self.current_action_idx]

    def is_complete(self, snapshot: Dict[str, Any]) -> bool:
        runelite = snapshot.get("runelite_data", {})
        progress = runelite.get("tutorial_progress", 0)
        return progress >= 510


# =============================================================================
# T23: FINANCIAL ADVISOR PHASE
# =============================================================================

class FinancialAdvisorPhase(PhaseHandler):
    """
    Handles the Financial Advisor phase (T23).

    Steps:
    1. Talk to Financial Advisor
    2. Open bank
    3. Close bank
    4. Talk to Financial Advisor
    5. Open poll booth
    6. Close poll booth
    7. Walk to next area
    """

    def get_phase(self) -> TutorialPhase:
        return TutorialPhase.FINANCIAL_ADVISOR

    def initialize(self, snapshot: Dict[str, Any]):
        self.actions = [
            PhaseAction("click_object", "Bank booth", {"action": "use"}),
            PhaseAction("close_interface", "Bank", {}),
            PhaseAction("click_object", "Poll booth", {"action": "use"}),
            PhaseAction("close_interface", "Poll", {}),
            PhaseAction("talk_to", "Financial Advisor", {}),
            PhaseAction("click_object", "Door", {"action": "open"}),
        ]

    def get_next_action(self, snapshot: Dict[str, Any]) -> Optional[PhaseAction]:
        if self.current_action_idx >= len(self.actions):
            return None
        return self.actions[self.current_action_idx]

    def is_complete(self, snapshot: Dict[str, Any]) -> bool:
        runelite = snapshot.get("runelite_data", {})
        progress = runelite.get("tutorial_progress", 0)
        return progress >= 525


# =============================================================================
# T24: BROTHER BRACE PHASE
# =============================================================================

class BrotherBracePhase(PhaseHandler):
    """
    Handles the Brother Brace (prayer) phase (T24).

    Steps:
    1. Talk to Brother Brace
    2. Open prayer tab
    3. Talk to Brother Brace
    4. Open friends tab
    5. Talk to Brother Brace
    6. Walk to next area
    """

    def get_phase(self) -> TutorialPhase:
        return TutorialPhase.BROTHER_BRACE

    def initialize(self, snapshot: Dict[str, Any]):
        self.actions = [
            PhaseAction("talk_to", "Brother Brace", {}),
            PhaseAction("open_tab", "prayer", {}),
            PhaseAction("talk_to", "Brother Brace", {}),
            PhaseAction("open_tab", "friends", {}),
            PhaseAction("talk_to", "Brother Brace", {}),
            PhaseAction("click_object", "Door", {"action": "open"}),
        ]

    def get_next_action(self, snapshot: Dict[str, Any]) -> Optional[PhaseAction]:
        if self.current_action_idx >= len(self.actions):
            return None
        return self.actions[self.current_action_idx]

    def is_complete(self, snapshot: Dict[str, Any]) -> bool:
        runelite = snapshot.get("runelite_data", {})
        progress = runelite.get("tutorial_progress", 0)
        return progress >= 610


# =============================================================================
# T25: MAGIC INSTRUCTOR PHASE
# =============================================================================

class MagicInstructorPhase(PhaseHandler):
    """
    Handles the Magic Instructor phase (T25).

    Steps:
    1. Talk to Magic Instructor
    2. Open magic tab
    3. Talk to Magic Instructor
    4. Cast Wind Strike on chicken
    5. Talk to Magic Instructor
    6. Choose mainland destination
    """

    def get_phase(self) -> TutorialPhase:
        return TutorialPhase.MAGIC_INSTRUCTOR

    def initialize(self, snapshot: Dict[str, Any]):
        self.actions = [
            PhaseAction("talk_to", "Magic Instructor", {}),
            PhaseAction("open_tab", "magic", {}),
            PhaseAction("talk_to", "Magic Instructor", {}),
            PhaseAction("cast_spell", "Wind Strike", {"target": "Chicken"}),
            PhaseAction("wait", "", {"condition": "combat_complete"}),
            PhaseAction("talk_to", "Magic Instructor", {}),
            PhaseAction("dialogue_option", "Yes", {}),
        ]

    def get_next_action(self, snapshot: Dict[str, Any]) -> Optional[PhaseAction]:
        if self.current_action_idx >= len(self.actions):
            return None
        return self.actions[self.current_action_idx]

    def is_complete(self, snapshot: Dict[str, Any]) -> bool:
        runelite = snapshot.get("runelite_data", {})
        progress = runelite.get("tutorial_progress", 0)
        return progress >= 1000


# =============================================================================
# TUTORIAL ORCHESTRATOR
# =============================================================================

class TutorialOrchestrator:
    """
    Orchestrates the entire Tutorial Island completion.

    Coordinates between phase handlers and manages transitions.
    """

    def __init__(self):
        self.phase_verifier = PhaseVerifier()
        self.phase_handlers: Dict[TutorialPhase, PhaseHandler] = {
            TutorialPhase.GIELINOR_GUIDE: GielinorGuidePhase(),
            TutorialPhase.SURVIVAL_EXPERT: SurvivalExpertPhase(),
            TutorialPhase.MASTER_CHEF: MasterChefPhase(),
            TutorialPhase.QUEST_GUIDE: QuestGuidePhase(),
            TutorialPhase.MINING_INSTRUCTOR: MiningInstructorPhase(),
            TutorialPhase.COMBAT_INSTRUCTOR: CombatInstructorPhase(),
            TutorialPhase.FINANCIAL_ADVISOR: FinancialAdvisorPhase(),
            TutorialPhase.BROTHER_BRACE: BrotherBracePhase(),
            TutorialPhase.MAGIC_INSTRUCTOR: MagicInstructorPhase(),
        }
        self.current_handler: Optional[PhaseHandler] = None
        self.started: bool = False

    def start(self, snapshot: Dict[str, Any]):
        """Start the tutorial from current state."""
        self.started = True
        self._update_handler(snapshot)

    def update(self, snapshot: Dict[str, Any]) -> Optional[PhaseAction]:
        """
        Update state and get next action.

        Returns:
            Next action to perform, or None if tutorial complete
        """
        if not self.started:
            return None

        # Check for phase transitions
        transition = self.phase_verifier.update(snapshot)
        if transition:
            self._update_handler(snapshot)

        # Get next action from current handler
        if self.current_handler:
            action = self.current_handler.get_next_action(snapshot)
            if action:
                return action

            # Check if phase complete
            if self.current_handler.is_complete(snapshot):
                self._update_handler(snapshot)
                return self.update(snapshot)

        return None

    def _update_handler(self, snapshot: Dict[str, Any]):
        """Update the current phase handler."""
        current_phase = self.phase_verifier.current_phase

        if current_phase in self.phase_handlers:
            self.current_handler = self.phase_handlers[current_phase]
            self.current_handler.initialize(snapshot)
        else:
            self.current_handler = None

    def is_complete(self) -> bool:
        """Check if tutorial is complete."""
        return self.phase_verifier.current_phase == TutorialPhase.COMPLETE

    def get_progress(self) -> Dict[str, Any]:
        """Get current tutorial progress."""
        return {
            "current_phase": self.phase_verifier.current_phase.value,
            "progress_percent": self.phase_verifier.get_phase_progress() * 100,
            "transitions": len(self.phase_verifier.transitions),
            "is_complete": self.is_complete(),
        }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Phase enum
    "TutorialPhase",

    # Detection (T26)
    "detect_phase_from_hint",
    "detect_phase_from_varbit",
    "detect_phase",

    # Verification (T27)
    "PhaseTransition",
    "PhaseVerifier",

    # Phase handlers (T17-T25)
    "PhaseAction",
    "PhaseHandler",
    "GielinorGuidePhase",
    "SurvivalExpertPhase",
    "MasterChefPhase",
    "QuestGuidePhase",
    "MiningInstructorPhase",
    "CombatInstructorPhase",
    "FinancialAdvisorPhase",
    "BrotherBracePhase",
    "MagicInstructorPhase",

    # Orchestrator
    "TutorialOrchestrator",
]
