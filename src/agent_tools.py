"""
Agent Tools Module

This module implements:
- T36: Build capture and annotate dataset tool
- T37: Add replay viewer for frame sequences
- T38: Define unified action API
- T39: Add timing variance (dwell, jitter)
- T40: Implement drag actions with jitter
- T41: Add human-in-the-loop approval toggle
- T42: Add hardware device enumeration
- T43: Add device-level input profiles
- T44: Detect display refresh rate
- T45-T47: Define parity criteria docs
- T48-T50: Human session comparison tools

Nightfall - 2026-01-07
"""
from __future__ import annotations

import json
import logging
import os
import platform
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# T36: CAPTURE AND ANNOTATE DATASET TOOL
# =============================================================================

@dataclass
class AnnotatedFrame:
    """A captured frame with annotations."""
    frame_id: str
    timestamp: str
    image_path: str
    snapshot: Dict[str, Any]
    annotations: Dict[str, Any] = field(default_factory=dict)
    labels: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DatasetCapture:
    """
    Tool for capturing and annotating gameplay frames (T36).

    Used to build training/reference datasets for the agent.
    """

    def __init__(self, dataset_path: Optional[Path] = None):
        self.dataset_path = dataset_path or Path("data/ml_dataset")
        self.dataset_path.mkdir(parents=True, exist_ok=True)
        self.frames: List[AnnotatedFrame] = []
        self.session_id: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.frame_count: int = 0

    def capture_frame(
        self,
        image: Any,
        snapshot: Dict[str, Any],
        labels: Optional[List[str]] = None,
        auto_annotate: bool = True,
    ) -> AnnotatedFrame:
        """
        Capture a frame with optional auto-annotation.

        Args:
            image: The captured image (PIL or numpy)
            snapshot: Game state snapshot
            labels: Manual labels for this frame
            auto_annotate: Whether to auto-generate annotations

        Returns:
            AnnotatedFrame object
        """
        self.frame_count += 1
        frame_id = f"{self.session_id}_{self.frame_count:06d}"

        # Save image
        image_filename = f"{frame_id}.png"
        image_path = self.dataset_path / "images" / image_filename
        image_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if hasattr(image, 'save'):
                image.save(str(image_path))
            else:
                from PIL import Image
                Image.fromarray(image).save(str(image_path))
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            image_path = Path("")

        # Generate annotations
        annotations = {}
        if auto_annotate:
            annotations = self._auto_annotate(snapshot)

        # Create frame record
        frame = AnnotatedFrame(
            frame_id=frame_id,
            timestamp=datetime.now().isoformat(),
            image_path=str(image_path),
            snapshot=snapshot,
            annotations=annotations,
            labels=labels or [],
            metadata={
                "session_id": self.session_id,
                "frame_number": self.frame_count,
            }
        )

        self.frames.append(frame)

        # Save frame data
        self._save_frame_data(frame)

        return frame

    def _auto_annotate(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-generate annotations from snapshot."""
        annotations = {}

        # Extract UI state
        ui = snapshot.get("ui", {})
        annotations["open_interface"] = ui.get("open_interface", "none")
        annotations["has_dialogue"] = len(ui.get("dialogue_options", [])) > 0
        annotations["hover_text"] = ui.get("hover_text", "")

        # Extract player state
        runelite = snapshot.get("runelite_data", {})
        annotations["tutorial_progress"] = runelite.get("tutorial_progress", 0)
        annotations["inventory_count"] = runelite.get("inventory_count", 0)
        annotations["has_npcs_visible"] = len(runelite.get("npcs_on_screen", [])) > 0

        # Extract derived state
        derived = snapshot.get("derived", {})
        location = derived.get("location", {})
        annotations["region"] = location.get("region", "unknown")
        annotations["activity_type"] = derived.get("activity", {}).get("type", "idle")

        return annotations

    def _save_frame_data(self, frame: AnnotatedFrame):
        """Save frame metadata to JSONL file."""
        data_path = self.dataset_path / "frames.jsonl"

        with open(data_path, "a", encoding="utf-8") as f:
            record = {
                "frame_id": frame.frame_id,
                "timestamp": frame.timestamp,
                "image_path": frame.image_path,
                "annotations": frame.annotations,
                "labels": frame.labels,
                "metadata": frame.metadata,
            }
            f.write(json.dumps(record) + "\n")

    def add_annotation(
        self,
        frame_id: str,
        key: str,
        value: Any,
    ):
        """Add an annotation to a frame."""
        for frame in self.frames:
            if frame.frame_id == frame_id:
                frame.annotations[key] = value
                break

    def add_label(self, frame_id: str, label: str):
        """Add a label to a frame."""
        for frame in self.frames:
            if frame.frame_id == frame_id:
                if label not in frame.labels:
                    frame.labels.append(label)
                break

    def export_dataset(self, output_path: Optional[Path] = None) -> Path:
        """
        Export the dataset to a structured format.

        Returns:
            Path to exported dataset
        """
        output_path = output_path or self.dataset_path / "export"
        output_path.mkdir(parents=True, exist_ok=True)

        # Export manifest
        manifest = {
            "session_id": self.session_id,
            "frame_count": self.frame_count,
            "exported_at": datetime.now().isoformat(),
            "frames": [
                {
                    "frame_id": f.frame_id,
                    "image_path": f.image_path,
                    "annotations": f.annotations,
                    "labels": f.labels,
                }
                for f in self.frames
            ]
        }

        manifest_path = output_path / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Exported dataset to {output_path}")
        return output_path


# =============================================================================
# T37: REPLAY VIEWER FOR FRAME SEQUENCES
# =============================================================================

@dataclass
class ReplayFrame:
    """A frame in a replay sequence."""
    frame_id: str
    timestamp: float
    image_path: str
    snapshot: Dict[str, Any]
    actions: List[Dict[str, Any]] = field(default_factory=list)


class ReplayRecorder:
    """
    Records gameplay sessions for replay (T37).

    Captures frames, actions, and state for review.
    """

    def __init__(self, output_path: Optional[Path] = None):
        self.output_path = output_path or Path("data/replays")
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.session_id: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.frames: List[ReplayFrame] = []
        self.start_time: float = 0.0
        self.is_recording: bool = False

    def start_recording(self):
        """Start a new recording session."""
        self.is_recording = True
        self.start_time = time.time()
        self.frames = []
        logger.info(f"Started recording session: {self.session_id}")

    def stop_recording(self) -> Path:
        """Stop recording and save the replay."""
        self.is_recording = False
        replay_path = self._save_replay()
        logger.info(f"Stopped recording. Saved to {replay_path}")
        return replay_path

    def record_frame(
        self,
        image: Any,
        snapshot: Dict[str, Any],
        actions: Optional[List[Dict[str, Any]]] = None,
    ):
        """Record a single frame."""
        if not self.is_recording:
            return

        frame_num = len(self.frames)
        frame_id = f"{self.session_id}_{frame_num:06d}"

        # Save image
        image_dir = self.output_path / self.session_id / "frames"
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / f"{frame_id}.png"

        try:
            if hasattr(image, 'save'):
                image.save(str(image_path))
            else:
                from PIL import Image
                Image.fromarray(image).save(str(image_path))
        except Exception as e:
            logger.error(f"Failed to save replay frame: {e}")
            return

        frame = ReplayFrame(
            frame_id=frame_id,
            timestamp=time.time() - self.start_time,
            image_path=str(image_path),
            snapshot=snapshot,
            actions=actions or [],
        )

        self.frames.append(frame)

    def _save_replay(self) -> Path:
        """Save the replay to disk."""
        replay_dir = self.output_path / self.session_id
        replay_dir.mkdir(parents=True, exist_ok=True)

        # Save replay manifest
        manifest = {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "duration": time.time() - self.start_time,
            "frame_count": len(self.frames),
            "frames": [
                {
                    "frame_id": f.frame_id,
                    "timestamp": f.timestamp,
                    "image_path": f.image_path,
                    "actions": f.actions,
                }
                for f in self.frames
            ]
        }

        manifest_path = replay_dir / "replay.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return replay_dir


class ReplayViewer:
    """
    Views recorded replay sessions (T37).

    Provides frame-by-frame navigation and analysis.
    """

    def __init__(self):
        self.current_replay: Optional[Dict[str, Any]] = None
        self.current_frame_idx: int = 0
        self.playback_speed: float = 1.0
        self.is_playing: bool = False

    def load_replay(self, replay_path: Path) -> bool:
        """Load a replay from disk."""
        manifest_path = replay_path / "replay.json"

        if not manifest_path.exists():
            logger.error(f"Replay not found: {manifest_path}")
            return False

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                self.current_replay = json.load(f)
            self.current_frame_idx = 0
            logger.info(f"Loaded replay: {self.current_replay['session_id']}")
            return True
        except Exception as e:
            logger.error(f"Failed to load replay: {e}")
            return False

    def get_frame(self, index: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get a specific frame or current frame."""
        if not self.current_replay:
            return None

        idx = index if index is not None else self.current_frame_idx
        frames = self.current_replay.get("frames", [])

        if 0 <= idx < len(frames):
            return frames[idx]
        return None

    def next_frame(self) -> Optional[Dict[str, Any]]:
        """Advance to next frame."""
        if not self.current_replay:
            return None

        frames = self.current_replay.get("frames", [])
        if self.current_frame_idx < len(frames) - 1:
            self.current_frame_idx += 1

        return self.get_frame()

    def prev_frame(self) -> Optional[Dict[str, Any]]:
        """Go to previous frame."""
        if not self.current_replay:
            return None

        if self.current_frame_idx > 0:
            self.current_frame_idx -= 1

        return self.get_frame()

    def seek(self, timestamp: float):
        """Seek to a specific timestamp."""
        if not self.current_replay:
            return

        frames = self.current_replay.get("frames", [])
        for i, frame in enumerate(frames):
            if frame["timestamp"] >= timestamp:
                self.current_frame_idx = i
                break

    def get_frame_count(self) -> int:
        """Get total frame count."""
        if not self.current_replay:
            return 0
        return len(self.current_replay.get("frames", []))


# =============================================================================
# T38: UNIFIED ACTION API
# =============================================================================

class ActionType(Enum):
    """Types of actions the agent can perform."""
    MOUSE_MOVE = "mouse_move"
    MOUSE_CLICK = "mouse_click"
    MOUSE_DRAG = "mouse_drag"
    MOUSE_SCROLL = "mouse_scroll"
    KEY_PRESS = "key_press"
    KEY_DOWN = "key_down"
    KEY_UP = "key_up"
    TYPE_TEXT = "type_text"
    WAIT = "wait"


@dataclass
class UnifiedAction:
    """
    Unified action representation (T38).

    All agent actions are represented in this format.
    """
    action_type: ActionType
    params: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    intent_id: str = ""
    requires_approval: bool = False

    # Result fields (filled after execution)
    executed: bool = False
    success: bool = False
    execution_time_ms: float = 0.0
    error: str = ""


class ActionBuilder:
    """Builder for creating unified actions."""

    @staticmethod
    def move(x: int, y: int, **kwargs) -> UnifiedAction:
        """Create a mouse move action."""
        return UnifiedAction(
            action_type=ActionType.MOUSE_MOVE,
            params={"x": x, "y": y, **kwargs},
        )

    @staticmethod
    def click(
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        **kwargs
    ) -> UnifiedAction:
        """Create a mouse click action."""
        params = {"button": button, **kwargs}
        if x is not None:
            params["x"] = x
        if y is not None:
            params["y"] = y
        return UnifiedAction(
            action_type=ActionType.MOUSE_CLICK,
            params=params,
        )

    @staticmethod
    def drag(
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        **kwargs
    ) -> UnifiedAction:
        """Create a mouse drag action."""
        return UnifiedAction(
            action_type=ActionType.MOUSE_DRAG,
            params={
                "start_x": start_x,
                "start_y": start_y,
                "end_x": end_x,
                "end_y": end_y,
                **kwargs
            },
        )

    @staticmethod
    def scroll(amount: int, **kwargs) -> UnifiedAction:
        """Create a mouse scroll action."""
        return UnifiedAction(
            action_type=ActionType.MOUSE_SCROLL,
            params={"amount": amount, **kwargs},
        )

    @staticmethod
    def key(key: str, **kwargs) -> UnifiedAction:
        """Create a key press action."""
        return UnifiedAction(
            action_type=ActionType.KEY_PRESS,
            params={"key": key, **kwargs},
        )

    @staticmethod
    def type_text(text: str, **kwargs) -> UnifiedAction:
        """Create a text typing action."""
        return UnifiedAction(
            action_type=ActionType.TYPE_TEXT,
            params={"text": text, **kwargs},
        )

    @staticmethod
    def wait(duration_ms: int) -> UnifiedAction:
        """Create a wait action."""
        return UnifiedAction(
            action_type=ActionType.WAIT,
            params={"duration_ms": duration_ms},
        )


# =============================================================================
# T39: TIMING VARIANCE (DWELL, JITTER)
# =============================================================================

@dataclass
class TimingProfile:
    """
    Profile for human-like timing variance (T39).

    Controls dwell times, reaction delays, and jitter.
    """
    # Click timing
    click_dwell_min_ms: int = 40
    click_dwell_max_ms: int = 80

    # Move timing
    move_duration_min_ms: int = 100
    move_duration_max_ms: int = 300

    # Reaction delay
    reaction_delay_min_ms: int = 150
    reaction_delay_max_ms: int = 400

    # Inter-action delay
    action_gap_min_ms: int = 50
    action_gap_max_ms: int = 200

    # Position jitter (pixels)
    position_jitter_min: int = -3
    position_jitter_max: int = 3

    # Timing jitter (percentage)
    timing_jitter_percent: float = 0.15


# Preset profiles
TIMING_PROFILES = {
    "subtle": TimingProfile(
        click_dwell_min_ms=45,
        click_dwell_max_ms=65,
        move_duration_min_ms=120,
        move_duration_max_ms=250,
        reaction_delay_min_ms=180,
        reaction_delay_max_ms=350,
        timing_jitter_percent=0.10,
    ),
    "normal": TimingProfile(),  # Default values
    "heavy": TimingProfile(
        click_dwell_min_ms=35,
        click_dwell_max_ms=100,
        move_duration_min_ms=80,
        move_duration_max_ms=400,
        reaction_delay_min_ms=120,
        reaction_delay_max_ms=500,
        position_jitter_min=-5,
        position_jitter_max=5,
        timing_jitter_percent=0.25,
    ),
}


class TimingVariance:
    """
    Applies human-like timing variance to actions (T39).
    """

    def __init__(self, profile: Optional[TimingProfile] = None):
        self.profile = profile or TimingProfile()

    def get_click_dwell(self) -> int:
        """Get randomized click dwell time in ms."""
        base = random.randint(
            self.profile.click_dwell_min_ms,
            self.profile.click_dwell_max_ms
        )
        jitter = int(base * self.profile.timing_jitter_percent * random.uniform(-1, 1))
        return max(20, base + jitter)

    def get_move_duration(self, distance: float) -> int:
        """Get randomized move duration based on distance."""
        # Base duration scales with distance
        base_per_px = 0.5  # ms per pixel
        base = int(distance * base_per_px)
        base = max(self.profile.move_duration_min_ms,
                   min(self.profile.move_duration_max_ms, base))
        jitter = int(base * self.profile.timing_jitter_percent * random.uniform(-1, 1))
        return max(50, base + jitter)

    def get_reaction_delay(self) -> int:
        """Get randomized reaction delay in ms."""
        base = random.randint(
            self.profile.reaction_delay_min_ms,
            self.profile.reaction_delay_max_ms
        )
        jitter = int(base * self.profile.timing_jitter_percent * random.uniform(-1, 1))
        return max(50, base + jitter)

    def get_action_gap(self) -> int:
        """Get randomized gap between actions in ms."""
        base = random.randint(
            self.profile.action_gap_min_ms,
            self.profile.action_gap_max_ms
        )
        return max(10, base)

    def apply_position_jitter(self, x: int, y: int) -> Tuple[int, int]:
        """Apply position jitter to coordinates."""
        jx = random.randint(
            self.profile.position_jitter_min,
            self.profile.position_jitter_max
        )
        jy = random.randint(
            self.profile.position_jitter_min,
            self.profile.position_jitter_max
        )
        return (x + jx, y + jy)


# =============================================================================
# T40: DRAG ACTIONS WITH JITTER
# =============================================================================

@dataclass
class DragConfig:
    """Configuration for drag actions (T40)."""
    # Start hesitation
    start_hesitation_min_ms: int = 30
    start_hesitation_max_ms: int = 100

    # End jitter (pixels)
    end_jitter_min: int = -5
    end_jitter_max: int = 5

    # Path curvature
    path_curvature: float = 0.1

    # Speed variance
    speed_min: float = 0.8
    speed_max: float = 1.2


class HumanDrag:
    """
    Implements human-like drag actions (T40).

    Includes start hesitation, path variance, and end jitter.
    """

    def __init__(self, config: Optional[DragConfig] = None):
        self.config = config or DragConfig()
        self.timing = TimingVariance()

    def generate_drag_path(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        steps: int = 20,
    ) -> List[Tuple[int, int, int]]:
        """
        Generate a human-like drag path.

        Returns:
            List of (x, y, delay_ms) waypoints
        """
        path = []

        sx, sy = start
        ex, ey = end

        # Apply end jitter
        ex += random.randint(self.config.end_jitter_min, self.config.end_jitter_max)
        ey += random.randint(self.config.end_jitter_min, self.config.end_jitter_max)

        # Generate curved path
        for i in range(steps + 1):
            t = i / steps

            # Basic interpolation
            x = int(sx + (ex - sx) * t)
            y = int(sy + (ey - sy) * t)

            # Add curvature (bezier-like)
            if 0 < t < 1:
                # Perpendicular offset
                dx = ex - sx
                dy = ey - sy
                perp_x = -dy * self.config.path_curvature
                perp_y = dx * self.config.path_curvature

                # Parabolic curve
                curve_factor = 4 * t * (1 - t)
                x += int(perp_x * curve_factor * random.uniform(-1, 1))
                y += int(perp_y * curve_factor * random.uniform(-1, 1))

            # Calculate delay
            delay = self.timing.get_move_duration(10)  # Per-step delay
            delay = int(delay * random.uniform(
                self.config.speed_min,
                self.config.speed_max
            ))

            path.append((x, y, delay))

        return path

    def get_start_hesitation(self) -> int:
        """Get start hesitation delay in ms."""
        return random.randint(
            self.config.start_hesitation_min_ms,
            self.config.start_hesitation_max_ms
        )


# =============================================================================
# T41: HUMAN-IN-THE-LOOP APPROVAL TOGGLE
# =============================================================================

class ApprovalLevel(Enum):
    """Levels of human approval required."""
    NONE = "none"              # No approval needed
    DANGEROUS = "dangerous"    # Only for dangerous actions
    ALL = "all"                # Approve all actions


@dataclass
class ApprovalRequest:
    """Request for human approval."""
    action: UnifiedAction
    reason: str
    context: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 30.0
    default_approve: bool = False


class ApprovalManager:
    """
    Manages human-in-the-loop approvals (T41).

    Provides a gate for actions that require human oversight.
    """

    # Actions that are considered dangerous
    DANGEROUS_ACTIONS = [
        "drop",
        "alch",
        "trade",
        "bank_all",
        "logout",
        "die",
    ]

    def __init__(self, level: ApprovalLevel = ApprovalLevel.NONE):
        self.level = level
        self.approval_callback: Optional[Callable[[ApprovalRequest], bool]] = None
        self.pending_requests: List[ApprovalRequest] = []
        self.approval_history: List[Tuple[ApprovalRequest, bool, float]] = []

    def set_callback(self, callback: Callable[[ApprovalRequest], bool]):
        """Set the callback for approval requests."""
        self.approval_callback = callback

    def requires_approval(self, action: UnifiedAction) -> bool:
        """Check if an action requires approval."""
        if self.level == ApprovalLevel.NONE:
            return False

        if self.level == ApprovalLevel.ALL:
            return True

        if self.level == ApprovalLevel.DANGEROUS:
            # Check if action is dangerous
            intent = action.intent_id.lower()
            return any(d in intent for d in self.DANGEROUS_ACTIONS)

        return False

    def request_approval(
        self,
        action: UnifiedAction,
        reason: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Request approval for an action.

        Returns:
            True if approved, False if denied
        """
        if not self.requires_approval(action):
            return True

        request = ApprovalRequest(
            action=action,
            reason=reason or f"Action {action.action_type.value} requires approval",
            context=context or {},
        )

        self.pending_requests.append(request)

        # If no callback, use default
        if not self.approval_callback:
            approved = request.default_approve
        else:
            approved = self.approval_callback(request)

        # Record result
        self.approval_history.append((request, approved, time.time()))
        self.pending_requests.remove(request)

        return approved

    def auto_approve_all(self):
        """Approve all pending requests."""
        for request in self.pending_requests[:]:
            self.approval_history.append((request, True, time.time()))
            self.pending_requests.remove(request)

    def auto_deny_all(self):
        """Deny all pending requests."""
        for request in self.pending_requests[:]:
            self.approval_history.append((request, False, time.time()))
            self.pending_requests.remove(request)


# =============================================================================
# T42: HARDWARE DEVICE ENUMERATION
# =============================================================================

@dataclass
class InputDevice:
    """Information about an input device."""
    device_type: str  # "mouse", "keyboard"
    name: str
    vendor_id: int = 0
    product_id: int = 0
    is_wireless: bool = False
    polling_rate_hz: int = 0
    dpi: int = 0  # For mice


class DeviceEnumerator:
    """
    Enumerates connected input devices (T42).

    Provides information about mice and keyboards.
    """

    def __init__(self):
        self.devices: List[InputDevice] = []
        self._enumerated: bool = False

    def enumerate(self) -> List[InputDevice]:
        """Enumerate all input devices."""
        self.devices = []

        if platform.system() == "Windows":
            self._enumerate_windows()
        elif platform.system() == "Linux":
            self._enumerate_linux()
        else:
            logger.warning(f"Device enumeration not implemented for {platform.system()}")

        self._enumerated = True
        return self.devices

    def _enumerate_windows(self):
        """Enumerate devices on Windows."""
        try:
            # Get basic device info using WMI
            import subprocess
            result = subprocess.run(
                ["wmic", "path", "Win32_PointingDevice", "get", "Name,PNPDeviceID"],
                capture_output=True,
                text=True
            )

            for line in result.stdout.strip().split("\n")[1:]:
                if line.strip():
                    parts = line.strip().split()
                    if parts:
                        self.devices.append(InputDevice(
                            device_type="mouse",
                            name=" ".join(parts[:-1]) if len(parts) > 1 else parts[0],
                        ))

            result = subprocess.run(
                ["wmic", "path", "Win32_Keyboard", "get", "Name,PNPDeviceID"],
                capture_output=True,
                text=True
            )

            for line in result.stdout.strip().split("\n")[1:]:
                if line.strip():
                    parts = line.strip().split()
                    if parts:
                        self.devices.append(InputDevice(
                            device_type="keyboard",
                            name=" ".join(parts[:-1]) if len(parts) > 1 else parts[0],
                        ))

        except Exception as e:
            logger.error(f"Windows device enumeration failed: {e}")

    def _enumerate_linux(self):
        """Enumerate devices on Linux."""
        try:
            import glob

            # Check /dev/input for devices
            for device_path in glob.glob("/dev/input/event*"):
                # Would need to parse /sys/class/input for details
                self.devices.append(InputDevice(
                    device_type="unknown",
                    name=device_path,
                ))

        except Exception as e:
            logger.error(f"Linux device enumeration failed: {e}")

    def get_mice(self) -> List[InputDevice]:
        """Get all mouse devices."""
        if not self._enumerated:
            self.enumerate()
        return [d for d in self.devices if d.device_type == "mouse"]

    def get_keyboards(self) -> List[InputDevice]:
        """Get all keyboard devices."""
        if not self._enumerated:
            self.enumerate()
        return [d for d in self.devices if d.device_type == "keyboard"]


# =============================================================================
# T43: DEVICE-LEVEL INPUT PROFILES
# =============================================================================

@dataclass
class InputProfile:
    """
    Device-level input profile (T43).

    Captures device-specific characteristics for timing modeling.
    """
    name: str = "default"

    # Mouse settings
    mouse_dpi: int = 800
    mouse_polling_rate_hz: int = 125
    mouse_acceleration: bool = False
    mouse_acceleration_curve: str = "none"

    # Keyboard settings
    keyboard_repeat_delay_ms: int = 500
    keyboard_repeat_rate_hz: int = 31

    # OS settings
    os_mouse_speed: int = 10  # 1-20 on Windows
    enhance_pointer_precision: bool = False

    # Derived timings
    min_movement_time_ms: int = 8  # Based on polling rate


# Common profiles
INPUT_PROFILES = {
    "default": InputProfile(),
    "gaming_mouse": InputProfile(
        name="gaming_mouse",
        mouse_dpi=1600,
        mouse_polling_rate_hz=1000,
        min_movement_time_ms=1,
    ),
    "office_mouse": InputProfile(
        name="office_mouse",
        mouse_dpi=800,
        mouse_polling_rate_hz=125,
        mouse_acceleration=True,
        min_movement_time_ms=8,
    ),
}


class ProfileManager:
    """Manages input device profiles (T43)."""

    def __init__(self):
        self.profiles: Dict[str, InputProfile] = INPUT_PROFILES.copy()
        self.active_profile: str = "default"

    def get_profile(self, name: Optional[str] = None) -> InputProfile:
        """Get a profile by name or the active profile."""
        name = name or self.active_profile
        return self.profiles.get(name, InputProfile())

    def set_active(self, name: str) -> bool:
        """Set the active profile."""
        if name in self.profiles:
            self.active_profile = name
            return True
        return False

    def add_profile(self, profile: InputProfile):
        """Add a new profile."""
        self.profiles[profile.name] = profile


# =============================================================================
# T44: DISPLAY REFRESH RATE DETECTION
# =============================================================================

class DisplayInfo:
    """Information about the display."""

    def __init__(self):
        self.refresh_rate_hz: int = 60
        self.resolution: Tuple[int, int] = (1920, 1080)
        self.scale_factor: float = 1.0
        self._detected: bool = False

    def detect(self):
        """Detect display properties."""
        if platform.system() == "Windows":
            self._detect_windows()
        else:
            self._detect_fallback()
        self._detected = True

    def _detect_windows(self):
        """Detect display info on Windows."""
        try:
            import ctypes
            user32 = ctypes.windll.user32

            # Get refresh rate
            hdc = user32.GetDC(0)
            self.refresh_rate_hz = ctypes.windll.gdi32.GetDeviceCaps(hdc, 116)  # VREFRESH
            user32.ReleaseDC(0, hdc)

            # Get resolution
            self.resolution = (
                user32.GetSystemMetrics(0),  # SM_CXSCREEN
                user32.GetSystemMetrics(1),  # SM_CYSCREEN
            )

            # Get DPI scaling
            try:
                shcore = ctypes.windll.shcore
                shcore.SetProcessDpiAwareness(2)
                dpi = ctypes.c_uint()
                shcore.GetDpiForMonitor(
                    user32.MonitorFromPoint(ctypes.c_long(0), ctypes.c_long(0), 2),
                    0,  # MDT_EFFECTIVE_DPI
                    ctypes.byref(dpi),
                    ctypes.byref(dpi)
                )
                self.scale_factor = dpi.value / 96.0
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Windows display detection failed: {e}")
            self._detect_fallback()

    def _detect_fallback(self):
        """Fallback display detection."""
        self.refresh_rate_hz = 60
        self.resolution = (1920, 1080)
        self.scale_factor = 1.0

    def get_frame_time_ms(self) -> float:
        """Get time per frame in milliseconds."""
        return 1000.0 / self.refresh_rate_hz


# =============================================================================
# T48-T50: HUMAN SESSION COMPARISON TOOLS
# =============================================================================

@dataclass
class SessionMetrics:
    """Metrics for comparing sessions."""
    total_actions: int = 0
    total_time_seconds: float = 0.0

    # Timing metrics
    avg_click_dwell_ms: float = 0.0
    avg_move_time_ms: float = 0.0
    avg_reaction_time_ms: float = 0.0

    # Accuracy metrics
    click_miss_rate: float = 0.0
    overshoot_rate: float = 0.0

    # Pattern metrics
    action_variance: float = 0.0
    timing_variance: float = 0.0


class SessionComparison:
    """
    Compares agent sessions to human baselines (T48-T50).
    """

    def __init__(self):
        self.human_baseline: Optional[SessionMetrics] = None
        self.agent_sessions: List[SessionMetrics] = []

    def load_human_baseline(self, baseline_path: Path) -> bool:
        """Load human baseline metrics."""
        try:
            with open(baseline_path, "r") as f:
                data = json.load(f)
            self.human_baseline = SessionMetrics(**data)
            return True
        except Exception as e:
            logger.error(f"Failed to load baseline: {e}")
            return False

    def compare_session(self, session: SessionMetrics) -> Dict[str, float]:
        """
        Compare an agent session to human baseline.

        Returns:
            Dict of metric names to deviation percentages
        """
        if not self.human_baseline:
            return {}

        deviations = {}

        # Compare timing
        if self.human_baseline.avg_click_dwell_ms > 0:
            deviations["click_dwell"] = abs(
                session.avg_click_dwell_ms - self.human_baseline.avg_click_dwell_ms
            ) / self.human_baseline.avg_click_dwell_ms * 100

        if self.human_baseline.avg_move_time_ms > 0:
            deviations["move_time"] = abs(
                session.avg_move_time_ms - self.human_baseline.avg_move_time_ms
            ) / self.human_baseline.avg_move_time_ms * 100

        if self.human_baseline.avg_reaction_time_ms > 0:
            deviations["reaction_time"] = abs(
                session.avg_reaction_time_ms - self.human_baseline.avg_reaction_time_ms
            ) / self.human_baseline.avg_reaction_time_ms * 100

        return deviations

    def is_within_threshold(
        self,
        session: SessionMetrics,
        threshold_percent: float = 20.0,
    ) -> bool:
        """Check if session metrics are within acceptable deviation."""
        deviations = self.compare_session(session)

        for metric, deviation in deviations.items():
            if deviation > threshold_percent:
                return False

        return True


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # T36: Dataset capture
    "AnnotatedFrame",
    "DatasetCapture",

    # T37: Replay
    "ReplayFrame",
    "ReplayRecorder",
    "ReplayViewer",

    # T38: Unified actions
    "ActionType",
    "UnifiedAction",
    "ActionBuilder",

    # T39: Timing variance
    "TimingProfile",
    "TIMING_PROFILES",
    "TimingVariance",

    # T40: Drag actions
    "DragConfig",
    "HumanDrag",

    # T41: Approval
    "ApprovalLevel",
    "ApprovalRequest",
    "ApprovalManager",

    # T42: Device enumeration
    "InputDevice",
    "DeviceEnumerator",

    # T43: Input profiles
    "InputProfile",
    "INPUT_PROFILES",
    "ProfileManager",

    # T44: Display info
    "DisplayInfo",

    # T48-T50: Session comparison
    "SessionMetrics",
    "SessionComparison",
]
