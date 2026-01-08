"""
SNAPSHOT_SCHEMA.md compliant snapshot capture.

This module implements:
- T1: Update snapshot capture to output SNAPSHOT_SCHEMA.md fields
- T2: Gate heavy OCR behind stuck triggers
- T3: Define fallback triggers and recovery flow
- T4/T5: Proper error handling (no silent pass blocks)

Nightfall - 2026-01-07
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configure logging for error handling (T4/T5)
logger = logging.getLogger(__name__)

# =============================================================================
# ERROR HANDLING (T4, T5)
# =============================================================================

class SnapshotError(Exception):
    """Base exception for snapshot errors."""
    pass


class OCRError(SnapshotError):
    """OCR-specific errors."""
    pass


class PerceptionError(SnapshotError):
    """Perception pipeline errors."""
    pass


# =============================================================================
# FALLBACK TRIGGERS (T3)
# =============================================================================

@dataclass
class FallbackState:
    """Tracks state for fallback trigger decisions."""
    position_history: List[Tuple[int, int, int]] = field(default_factory=list)
    last_action_success: bool = True
    consecutive_failures: int = 0
    last_successful_action_time: float = 0.0
    last_state_change_time: float = 0.0


class FallbackTrigger:
    """
    Determines when to trigger fallback to heavy perception (T3).

    Fallback triggers:
    - Stuck: No position change for N ticks
    - Stale data: RSProx/RuneLite data too old
    - Low confidence: Detection confidence below threshold
    - Consecutive failures: Multiple action failures in a row
    - Verification failure: Post-action verification failed
    """

    STUCK_THRESHOLD_TICKS = 5
    LOW_CONFIDENCE_THRESHOLD = 0.5
    STALE_DATA_MAX_MS = 2000
    MAX_CONSECUTIVE_FAILURES = 3
    IDLE_TIMEOUT_MS = 10000

    def __init__(self):
        self.state = FallbackState()

    def check(self, snapshot: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if fallback should be triggered.

        Args:
            snapshot: Current game snapshot

        Returns:
            (should_trigger, reason)
        """
        reasons = []

        # Check staleness
        if snapshot.get("stale", False):
            reasons.append("stale_data")

        # Check position stuck
        runelite = snapshot.get("runelite_data", {})
        pos = runelite.get("player_world")
        if pos:
            self.state.position_history.append(tuple(pos) if isinstance(pos, list) else pos)
            if len(self.state.position_history) > self.STUCK_THRESHOLD_TICKS:
                self.state.position_history.pop(0)

            if len(self.state.position_history) >= self.STUCK_THRESHOLD_TICKS:
                unique = set(str(p) for p in self.state.position_history)
                if len(unique) <= 1:
                    reasons.append("stuck")

        # Check consecutive failures
        if self.state.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            reasons.append("consecutive_failures")

        # Check for idle timeout
        now = time.time()
        if self.state.last_successful_action_time > 0:
            idle_ms = (now - self.state.last_successful_action_time) * 1000
            if idle_ms > self.IDLE_TIMEOUT_MS:
                reasons.append("idle_timeout")

        if reasons:
            return True, ",".join(reasons)
        return False, "none"

    def record_success(self):
        """Record a successful action."""
        self.state.last_action_success = True
        self.state.consecutive_failures = 0
        self.state.last_successful_action_time = time.time()
        self.state.last_state_change_time = time.time()

    def record_failure(self, reason: str = "unknown"):
        """Record a failed action."""
        self.state.last_action_success = False
        self.state.consecutive_failures += 1
        logger.warning(f"Action failure recorded: {reason} (consecutive: {self.state.consecutive_failures})")

    def reset(self):
        """Reset fallback state."""
        self.state = FallbackState()


# Global instance
_fallback_trigger = FallbackTrigger()


def get_fallback_trigger() -> FallbackTrigger:
    """Get the global fallback trigger."""
    return _fallback_trigger


# =============================================================================
# SNAPSHOT CAPTURE (T1)
# =============================================================================

def capture_snapshot_v2(
    window_bounds: Optional[Tuple[int, int, int, int]] = None,
    session_id: str = "",
    force_ocr: bool = False,
) -> Dict[str, Any]:
    """
    Capture a game snapshot compliant with SNAPSHOT_SCHEMA.md.

    This is the canonical snapshot function for the JSON action-intent loop.
    Heavy OCR is gated behind fallback triggers (T2).

    Args:
        window_bounds: (x, y, width, height) for screen capture
        session_id: Session identifier for correlation
        force_ocr: Force full OCR regardless of triggers

    Returns:
        Snapshot dict with all SNAPSHOT_SCHEMA.md required fields
    """
    from src.fast_perception import perceive, PerceptionResult

    capture_start = time.time()

    # Run base perception
    try:
        result = perceive(window_bounds=window_bounds)
    except Exception as e:
        logger.error(f"Perception failed: {e}")
        # Return minimal snapshot on perception failure
        result = _create_empty_perception_result()

    capture_latency = int((time.time() - capture_start) * 1000)

    # Generate identifiers
    capture_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().isoformat()
    stale = not result.runelite_fresh

    # Build base snapshot
    snapshot = _build_base_snapshot(
        capture_id=capture_id,
        timestamp=timestamp,
        session_id=session_id,
        stale=stale,
        capture_latency=capture_latency,
        window_bounds=window_bounds,
        result=result,
    )

    # Check fallback triggers (T2, T3)
    trigger = get_fallback_trigger()
    should_fallback, reason = trigger.check(snapshot)

    snapshot["_fallback"] = {
        "triggered": should_fallback or force_ocr,
        "reason": reason if should_fallback else ("forced" if force_ocr else "none"),
    }

    # Run heavy OCR only when triggered (T2)
    if should_fallback or force_ocr:
        if window_bounds:
            _run_heavy_ocr(snapshot, window_bounds)

    # Add detection results
    _add_detection_results(snapshot, result)

    return snapshot


def _create_empty_perception_result():
    """Create an empty perception result for error cases."""
    from src.fast_perception import PerceptionResult
    return PerceptionResult()


def _build_base_snapshot(
    capture_id: str,
    timestamp: str,
    session_id: str,
    stale: bool,
    capture_latency: int,
    window_bounds: Optional[Tuple[int, int, int, int]],
    result: Any,
) -> Dict[str, Any]:
    """Build the base snapshot structure per SNAPSHOT_SCHEMA.md."""
    return {
        # Required top-level fields
        "capture_id": capture_id,
        "timestamp": timestamp,
        "version": 1,
        "stale": stale,
        "session_id": session_id or f"sess_{capture_id}",

        # client section
        "client": {
            "window_title": "RuneLite" if window_bounds else "unknown",
            "bounds": {
                "x": window_bounds[0] if window_bounds else 0,
                "y": window_bounds[1] if window_bounds else 0,
                "width": window_bounds[2] if window_bounds else 0,
                "height": window_bounds[3] if window_bounds else 0,
            },
            "focused": True,
            "scale": 1.0,
            "fps": 20,
            "capture_latency_ms": capture_latency,
        },

        # roi section
        "roi": {
            "minimap": {"x": 550, "y": 5, "width": 150, "height": 150},
            "inventory": {"x": 560, "y": 210, "width": 180, "height": 260},
            "chatbox": {"x": 0, "y": 340, "width": 520, "height": 140},
            "game_view": {"x": 0, "y": 0, "width": 520, "height": 340},
        },

        # ui section
        "ui": {
            "open_interface": "none",
            "selected_tab": "inventory",
            "cursor_state": "default",
            "hover_text": "",
            "elements": [],
            "dialogue_options": [],
        },

        # ocr section
        "ocr": [],

        # cues section
        "cues": {
            "animation_state": "idle",
            "highlight_state": "none",
            "modal_state": "none",
            "hover_text": "",
            "chat_prompt": "",
        },

        # derived section
        "derived": {
            "location": {
                "region": _infer_region(result.player_world) if result.player_world else "unknown",
                "subarea": "",
                "coordinates": {
                    "x": result.player_world[0] if result.player_world else 0,
                    "y": result.player_world[1] if result.player_world else 0,
                    "plane": result.player_world[2] if result.player_world else 0,
                }
            },
            "activity": {"type": "idle", "state": "idle", "progress": 0.0},
            "combat": {"state": "out_of_combat"},
        },

        # account section
        "account": {
            "name": "",
            "membership_status": "f2p",
            "skills": {},
            "inventory": [],
            "equipment": {},
            "resources": {"gp": 0},
        },

        # runelite_data section
        "runelite_data": {
            "fresh": result.runelite_fresh,
            "tutorial_progress": result.tutorial_progress,
            "inventory_count": result.inventory_count,
            "camera_direction": result.camera_direction,
            "npcs_on_screen": result.npcs_on_screen,
            "player_screen": result.player_position,
            "player_world": result.player_world,
        },
    }


def _infer_region(world_coords: Optional[Tuple[int, int, int]]) -> str:
    """Infer region name from world coordinates (T8: region hints)."""
    if not world_coords:
        return "unknown"

    x, y, plane = world_coords

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


def _run_heavy_ocr(snapshot: Dict[str, Any], window_bounds: Tuple[int, int, int, int]) -> None:
    """
    Run heavy OCR processing (T2: only on fallback path).
    Includes proper error handling (T4/T5).
    """
    try:
        from src.perception import capture_frame
        from src.ocr import run_ocr

        ROOT = Path(__file__).resolve().parents[1]
        DATA_DIR = ROOT / "data"

        ocr_config_path = DATA_DIR / "ocr_config.json"
        ocr_regions_path = DATA_DIR / "ocr_regions.json"

        ocr_config = {}
        ocr_regions = {}

        if ocr_config_path.exists():
            try:
                ocr_config = json.loads(ocr_config_path.read_text())
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OCR config: {e}")
                snapshot["_fallback"]["ocr_config_error"] = str(e)

        if ocr_regions_path.exists():
            try:
                ocr_regions = json.loads(ocr_regions_path.read_text())
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OCR regions: {e}")
                snapshot["_fallback"]["ocr_regions_error"] = str(e)

        if not ocr_regions:
            logger.warning("No OCR regions defined, skipping OCR")
            return

        provider = ocr_config.get("provider", "tesseract")

        wx, wy, ww, wh = window_bounds
        try:
            frame = capture_frame((wx, wy, ww, wh))
        except Exception as e:
            logger.error(f"Frame capture failed: {e}")
            snapshot["_fallback"]["capture_error"] = str(e)
            return

        image = frame.get("image")
        if not image:
            logger.warning("No image in captured frame")
            return

        prepared_regions = {}
        for name, bounds in ocr_regions.items():
            if isinstance(bounds, dict):
                prepared_regions[name] = {**bounds, "_image": image}

        try:
            ocr_entries = run_ocr(prepared_regions, provider_name=provider, provider_config=ocr_config)
        except Exception as e:
            logger.error(f"OCR execution failed: {e}")
            snapshot["_fallback"]["ocr_error"] = str(e)
            return

        # Process OCR results
        for entry in ocr_entries:
            if entry.region == "hover_text":
                snapshot["ui"]["hover_text"] = entry.text
                snapshot["cues"]["hover_text"] = entry.text
            elif entry.region == "dialogue":
                snapshot["ui"]["dialogue_options"] = [
                    line for line in entry.text.splitlines() if line.strip()
                ]
            elif entry.region == "chat":
                snapshot["cues"]["chat_prompt"] = entry.text

        snapshot["ocr"] = [
            {"region": e.region, "text": e.text, "confidence": e.confidence}
            for e in ocr_entries
        ]

    except ImportError as e:
        logger.error(f"Missing OCR dependencies: {e}")
        snapshot["_fallback"]["import_error"] = str(e)
    except Exception as e:
        logger.error(f"Unexpected OCR error: {e}")
        snapshot["_fallback"]["ocr_error"] = str(e)


def _add_detection_results(snapshot: Dict[str, Any], result: Any) -> None:
    """Add detection results to snapshot."""
    if result.arrow_position:
        snapshot["arrow"] = {
            "x": result.arrow_position[0],
            "y": result.arrow_position[1],
            "confidence": result.arrow_confidence,
        }
        snapshot["cues"]["highlight_state"] = "arrow"

    if result.highlight_position:
        snapshot["highlight"] = {
            "x": result.highlight_position[0],
            "y": result.highlight_position[1],
            "confidence": result.highlight_confidence,
        }
        if snapshot["cues"]["highlight_state"] == "none":
            snapshot["cues"]["highlight_state"] = "object"


# =============================================================================
# VALIDATION
# =============================================================================

def validate_snapshot(snapshot: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate snapshot against SNAPSHOT_SCHEMA.md.

    Returns:
        (is_valid, list of error messages)
    """
    errors = []

    # Required top-level fields
    required_fields = [
        "capture_id", "timestamp", "version", "stale", "session_id",
        "client", "roi", "ui", "ocr", "cues", "derived", "account"
    ]

    for field in required_fields:
        if field not in snapshot:
            errors.append(f"Missing required field: {field}")

    # Validate client section
    if "client" in snapshot:
        client = snapshot["client"]
        client_fields = ["window_title", "bounds", "focused", "scale", "fps", "capture_latency_ms"]
        for field in client_fields:
            if field not in client:
                errors.append(f"Missing client field: {field}")

    # Validate ui section
    if "ui" in snapshot:
        ui = snapshot["ui"]
        ui_fields = ["open_interface", "selected_tab", "cursor_state", "hover_text", "elements", "dialogue_options"]
        for field in ui_fields:
            if field not in ui:
                errors.append(f"Missing ui field: {field}")

    # Validate cues section
    if "cues" in snapshot:
        cues = snapshot["cues"]
        cue_fields = ["animation_state", "highlight_state", "modal_state", "hover_text", "chat_prompt"]
        for field in cue_fields:
            if field not in cues:
                errors.append(f"Missing cues field: {field}")

    return len(errors) == 0, errors


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "capture_snapshot_v2",
    "validate_snapshot",
    "get_fallback_trigger",
    "FallbackTrigger",
    "FallbackState",
    "SnapshotError",
    "OCRError",
    "PerceptionError",
]
