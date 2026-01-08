"""
Perception Infrastructure Module

This module implements:
- T28: Client window discovery and focus tracking
- T29: Screen capture with FPS and ROI configuration
- T30: Capture latency and dropped-frame metrics
- T31: OCR backend with pluggable providers
- T32: UI element detector for core panels
- T33: Minimap parsing for region inference
- T34: Cursor state and hover text extraction

Nightfall - 2026-01-07
"""
from __future__ import annotations

import logging
import platform
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# T28: CLIENT WINDOW DISCOVERY AND FOCUS TRACKING
# =============================================================================

@dataclass
class WindowInfo:
    """Information about a game client window."""
    title: str
    hwnd: Optional[int] = None  # Windows handle
    pid: Optional[int] = None   # Process ID
    bounds: Tuple[int, int, int, int] = (0, 0, 800, 600)  # x, y, w, h
    is_focused: bool = False
    is_visible: bool = True
    client_type: str = "unknown"  # "runelite", "osrs", "vanilla"


class WindowTracker:
    """
    Tracks and discovers game client windows (T28).

    Supports multiple client types and monitors focus state.
    """

    # Window title patterns for different clients
    WINDOW_PATTERNS = {
        "runelite": ["RuneLite", "RuneLite -", "Old School RuneScape"],
        "osrs": ["Old School RuneScape"],
        "vanilla": ["Jagex Launcher"],
    }

    def __init__(self):
        self.current_window: Optional[WindowInfo] = None
        self.known_windows: Dict[int, WindowInfo] = {}
        self.last_focus_time: float = 0.0
        self.focus_lost_count: int = 0

    def discover_windows(self) -> List[WindowInfo]:
        """
        Discover all game client windows on the system.

        Returns:
            List of discovered game windows
        """
        windows = []

        if platform.system() == "Windows":
            try:
                windows = self._discover_windows_win32()
            except Exception as e:
                logger.error(f"Window discovery failed: {e}")
        else:
            logger.warning(f"Window discovery not implemented for {platform.system()}")

        return windows

    def _discover_windows_win32(self) -> List[WindowInfo]:
        """Discover windows on Windows using win32 API."""
        windows = []

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32

            def enum_callback(hwnd, results):
                if not user32.IsWindowVisible(hwnd):
                    return True

                length = user32.GetWindowTextLengthW(hwnd) + 1
                title = ctypes.create_unicode_buffer(length)
                user32.GetWindowTextW(hwnd, title, length)
                title_str = title.value

                # Check if it's a game window
                for client_type, patterns in self.WINDOW_PATTERNS.items():
                    if any(p in title_str for p in patterns):
                        # Get window bounds
                        rect = wintypes.RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))

                        # Get process ID
                        pid = wintypes.DWORD()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

                        # Check focus
                        is_focused = user32.GetForegroundWindow() == hwnd

                        window = WindowInfo(
                            title=title_str,
                            hwnd=hwnd,
                            pid=pid.value,
                            bounds=(rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top),
                            is_focused=is_focused,
                            is_visible=True,
                            client_type=client_type,
                        )
                        results.append(window)
                        break

                return True

            results = []
            enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(enum_proc(enum_callback), id(results))

            windows = results

        except ImportError:
            logger.warning("ctypes not available for window discovery")
        except Exception as e:
            logger.error(f"Win32 window discovery error: {e}")

        return windows

    def get_focused_window(self) -> Optional[WindowInfo]:
        """Get the currently focused game window."""
        windows = self.discover_windows()

        for window in windows:
            if window.is_focused:
                self.current_window = window
                self.last_focus_time = time.time()
                return window

        return None

    def is_game_focused(self) -> bool:
        """Check if any game window is currently focused."""
        window = self.get_focused_window()
        return window is not None

    def focus_window(self, window: WindowInfo) -> bool:
        """Attempt to focus a game window."""
        if platform.system() != "Windows" or window.hwnd is None:
            return False

        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetForegroundWindow(window.hwnd)
            time.sleep(0.1)
            return True
        except Exception as e:
            logger.error(f"Failed to focus window: {e}")
            return False

    def track_focus_loss(self) -> bool:
        """
        Track if focus has been lost and count occurrences.

        Returns:
            True if focus was lost since last check
        """
        if not self.is_game_focused():
            self.focus_lost_count += 1
            return True
        return False

    def get_window_bounds(self) -> Optional[Tuple[int, int, int, int]]:
        """Get bounds of current game window."""
        if self.current_window:
            return self.current_window.bounds

        window = self.get_focused_window()
        if window:
            return window.bounds

        return None


# =============================================================================
# T29: SCREEN CAPTURE WITH FPS AND ROI CONFIGURATION
# =============================================================================

@dataclass
class CaptureConfig:
    """Configuration for screen capture."""
    target_fps: int = 20
    roi: Optional[Tuple[int, int, int, int]] = None  # Region of interest
    format: str = "RGB"  # "RGB", "BGR", "RGBA"
    quality: int = 100  # JPEG quality if compressed
    use_mss: bool = True  # Use mss library for fast capture
    buffer_frames: int = 3  # Number of frames to buffer


@dataclass
class CapturedFrame:
    """A captured screen frame."""
    image: Any  # PIL Image or numpy array
    timestamp: float
    frame_number: int
    capture_time_ms: float
    bounds: Tuple[int, int, int, int]
    is_valid: bool = True


class ScreenCapture:
    """
    High-performance screen capture with ROI support (T29).

    Supports configurable FPS and region-of-interest capture.
    """

    def __init__(self, config: Optional[CaptureConfig] = None):
        self.config = config or CaptureConfig()
        self.frame_count: int = 0
        self.last_capture_time: float = 0.0
        self.frame_buffer: List[CapturedFrame] = []

    def capture(
        self,
        bounds: Optional[Tuple[int, int, int, int]] = None,
    ) -> CapturedFrame:
        """
        Capture the screen or a specific region.

        Args:
            bounds: (x, y, w, h) region to capture, or None for full screen

        Returns:
            CapturedFrame with the captured image
        """
        start_time = time.time()
        self.frame_count += 1

        # Use ROI from config if bounds not specified
        capture_bounds = bounds or self.config.roi or (0, 0, 1920, 1080)

        image = None
        is_valid = True

        try:
            if self.config.use_mss:
                image = self._capture_mss(capture_bounds)
            else:
                image = self._capture_pil(capture_bounds)
        except Exception as e:
            logger.error(f"Screen capture failed: {e}")
            is_valid = False

        capture_time_ms = (time.time() - start_time) * 1000
        self.last_capture_time = time.time()

        frame = CapturedFrame(
            image=image,
            timestamp=time.time(),
            frame_number=self.frame_count,
            capture_time_ms=capture_time_ms,
            bounds=capture_bounds,
            is_valid=is_valid,
        )

        # Buffer management
        self.frame_buffer.append(frame)
        if len(self.frame_buffer) > self.config.buffer_frames:
            self.frame_buffer.pop(0)

        return frame

    def _capture_mss(self, bounds: Tuple[int, int, int, int]) -> Any:
        """Capture using mss library (fast)."""
        try:
            import mss
            import numpy as np

            x, y, w, h = bounds
            with mss.mss() as sct:
                monitor = {"left": x, "top": y, "width": w, "height": h}
                screenshot = sct.grab(monitor)
                return np.array(screenshot)
        except ImportError:
            logger.warning("mss not available, falling back to PIL")
            return self._capture_pil(bounds)

    def _capture_pil(self, bounds: Tuple[int, int, int, int]) -> Any:
        """Capture using PIL/Pillow."""
        try:
            from PIL import ImageGrab

            x, y, w, h = bounds
            return ImageGrab.grab(bbox=(x, y, x + w, y + h))
        except Exception as e:
            logger.error(f"PIL capture failed: {e}")
            return None

    def get_target_interval(self) -> float:
        """Get target time between captures in seconds."""
        return 1.0 / self.config.target_fps

    def should_capture(self) -> bool:
        """Check if it's time for next capture based on target FPS."""
        if self.last_capture_time == 0:
            return True

        elapsed = time.time() - self.last_capture_time
        return elapsed >= self.get_target_interval()


# =============================================================================
# T30: CAPTURE LATENCY AND DROPPED-FRAME METRICS
# =============================================================================

@dataclass
class CaptureMetrics:
    """Metrics for screen capture performance."""
    total_frames: int = 0
    dropped_frames: int = 0
    total_capture_time_ms: float = 0.0
    min_capture_time_ms: float = float('inf')
    max_capture_time_ms: float = 0.0
    last_10_times_ms: List[float] = field(default_factory=list)
    session_start: float = 0.0

    @property
    def avg_capture_time_ms(self) -> float:
        if self.total_frames == 0:
            return 0.0
        return self.total_capture_time_ms / self.total_frames

    @property
    def drop_rate(self) -> float:
        if self.total_frames == 0:
            return 0.0
        return self.dropped_frames / self.total_frames

    @property
    def fps(self) -> float:
        if self.session_start == 0 or self.total_frames == 0:
            return 0.0
        elapsed = time.time() - self.session_start
        return self.total_frames / elapsed if elapsed > 0 else 0.0


class MetricsTracker:
    """
    Tracks capture performance metrics (T30).

    Monitors latency, frame drops, and FPS.
    """

    def __init__(self, target_fps: int = 20):
        self.target_fps = target_fps
        self.metrics = CaptureMetrics(session_start=time.time())
        self.last_frame_time: float = 0.0

    def record_frame(self, capture_time_ms: float, is_valid: bool = True):
        """Record a captured frame."""
        self.metrics.total_frames += 1
        self.metrics.total_capture_time_ms += capture_time_ms

        # Track min/max
        if capture_time_ms < self.metrics.min_capture_time_ms:
            self.metrics.min_capture_time_ms = capture_time_ms
        if capture_time_ms > self.metrics.max_capture_time_ms:
            self.metrics.max_capture_time_ms = capture_time_ms

        # Track last 10 for recent average
        self.metrics.last_10_times_ms.append(capture_time_ms)
        if len(self.metrics.last_10_times_ms) > 10:
            self.metrics.last_10_times_ms.pop(0)

        # Check for dropped frames
        if self.last_frame_time > 0:
            expected_interval = 1000.0 / self.target_fps
            actual_interval = (time.time() - self.last_frame_time) * 1000

            if actual_interval > expected_interval * 1.5:
                # Frame was likely dropped
                dropped = int((actual_interval / expected_interval) - 1)
                self.metrics.dropped_frames += dropped

        if not is_valid:
            self.metrics.dropped_frames += 1

        self.last_frame_time = time.time()

    def get_recent_avg_ms(self) -> float:
        """Get average of last 10 frame capture times."""
        if not self.metrics.last_10_times_ms:
            return 0.0
        return sum(self.metrics.last_10_times_ms) / len(self.metrics.last_10_times_ms)

    def is_healthy(self) -> bool:
        """Check if capture performance is healthy."""
        # Healthy if: FPS close to target and drop rate < 5%
        return (
            self.metrics.fps >= self.target_fps * 0.9 and
            self.metrics.drop_rate < 0.05
        )

    def reset(self):
        """Reset metrics for new session."""
        self.metrics = CaptureMetrics(session_start=time.time())
        self.last_frame_time = 0.0


# =============================================================================
# T31: OCR BACKEND WITH PLUGGABLE PROVIDERS
# =============================================================================

class OCRProvider(ABC):
    """Abstract base class for OCR providers."""

    @abstractmethod
    def recognize(
        self,
        image: Any,
        region_name: str = "",
    ) -> Tuple[str, float]:
        """
        Recognize text in an image.

        Args:
            image: Image to process (PIL Image or numpy array)
            region_name: Optional name of the region for context

        Returns:
            (recognized_text, confidence)
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available."""
        pass


class TesseractProvider(OCRProvider):
    """OCR using Tesseract."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._tesseract_cmd = self.config.get("tesseract_cmd", "tesseract")
        self._available: Optional[bool] = None

    def recognize(self, image: Any, region_name: str = "") -> Tuple[str, float]:
        try:
            import pytesseract

            # Configure pytesseract
            if self.config.get("tesseract_cmd"):
                pytesseract.pytesseract.tesseract_cmd = self.config["tesseract_cmd"]

            # Run OCR
            text = pytesseract.image_to_string(image)

            # Get confidence
            try:
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                confidences = [int(c) for c in data['conf'] if int(c) > 0]
                avg_conf = sum(confidences) / len(confidences) if confidences else 0
                confidence = avg_conf / 100.0
            except Exception:
                confidence = 0.5  # Default confidence

            return text.strip(), confidence
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            return "", 0.0

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available

        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self._available = True
        except Exception:
            self._available = False

        return self._available


class EasyOCRProvider(OCRProvider):
    """OCR using EasyOCR."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._reader = None
        self._available: Optional[bool] = None

    def recognize(self, image: Any, region_name: str = "") -> Tuple[str, float]:
        try:
            import easyocr
            import numpy as np

            if self._reader is None:
                self._reader = easyocr.Reader(['en'], gpu=False)

            # Convert to numpy if needed
            if hasattr(image, 'numpy'):
                img_array = np.array(image)
            else:
                img_array = image

            results = self._reader.readtext(img_array)

            # Combine all detected text
            texts = []
            confidences = []
            for bbox, text, conf in results:
                texts.append(text)
                confidences.append(conf)

            full_text = " ".join(texts)
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

            return full_text.strip(), avg_conf
        except Exception as e:
            logger.error(f"EasyOCR failed: {e}")
            return "", 0.0

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available

        try:
            import easyocr
            self._available = True
        except ImportError:
            self._available = False

        return self._available


class NoopProvider(OCRProvider):
    """No-op OCR provider for testing."""

    def recognize(self, image: Any, region_name: str = "") -> Tuple[str, float]:
        return "", 0.0

    def is_available(self) -> bool:
        return True


class OCRManager:
    """
    Manages OCR providers and delegates recognition (T31).

    Supports multiple providers with automatic fallback.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.providers: Dict[str, OCRProvider] = {}
        self.default_provider: str = "tesseract"

        # Initialize providers
        self._init_providers()

    def _init_providers(self):
        """Initialize available OCR providers."""
        self.providers["tesseract"] = TesseractProvider(self.config)
        self.providers["easyocr"] = EasyOCRProvider(self.config)
        self.providers["noop"] = NoopProvider()

        # Set default to first available
        for name, provider in self.providers.items():
            if provider.is_available() and name != "noop":
                self.default_provider = name
                break

    def recognize(
        self,
        image: Any,
        provider_name: Optional[str] = None,
        region_name: str = "",
    ) -> Tuple[str, float]:
        """
        Recognize text in an image.

        Args:
            image: Image to process
            provider_name: Specific provider to use, or None for default
            region_name: Optional region name for context

        Returns:
            (recognized_text, confidence)
        """
        provider_name = provider_name or self.default_provider
        provider = self.providers.get(provider_name)

        if not provider or not provider.is_available():
            # Fall back to another provider
            for name, p in self.providers.items():
                if p.is_available() and name != "noop":
                    provider = p
                    break
            else:
                return "", 0.0

        return provider.recognize(image, region_name)

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return [name for name, p in self.providers.items() if p.is_available()]


# =============================================================================
# T32: UI ELEMENT DETECTOR FOR CORE PANELS
# =============================================================================

class UIElement(Enum):
    """Types of UI elements."""
    TAB_COMBAT = "tab_combat"
    TAB_SKILLS = "tab_skills"
    TAB_QUEST = "tab_quest"
    TAB_INVENTORY = "tab_inventory"
    TAB_EQUIPMENT = "tab_equipment"
    TAB_PRAYER = "tab_prayer"
    TAB_MAGIC = "tab_magic"
    TAB_FRIENDS = "tab_friends"
    TAB_SETTINGS = "tab_settings"
    MINIMAP = "minimap"
    CHATBOX = "chatbox"
    GAME_VIEW = "game_view"
    DIALOGUE = "dialogue"
    BANK_INTERFACE = "bank_interface"


@dataclass
class DetectedElement:
    """A detected UI element."""
    element_type: UIElement
    bounds: Tuple[int, int, int, int]  # x, y, w, h
    confidence: float
    is_active: bool = False
    content: str = ""


# Fixed Classic Layout positions (relative to window)
FIXED_LAYOUT_ELEMENTS = {
    UIElement.TAB_COMBAT: (526, 168, 33, 36),
    UIElement.TAB_SKILLS: (559, 168, 33, 36),
    UIElement.TAB_QUEST: (592, 168, 33, 36),
    UIElement.TAB_INVENTORY: (625, 168, 33, 36),
    UIElement.TAB_EQUIPMENT: (658, 168, 33, 36),
    UIElement.TAB_PRAYER: (691, 168, 33, 36),
    UIElement.TAB_MAGIC: (724, 168, 33, 36),
    UIElement.MINIMAP: (550, 5, 155, 155),
    UIElement.CHATBOX: (0, 340, 520, 140),
    UIElement.GAME_VIEW: (0, 0, 520, 340),
}


class UIDetector:
    """
    Detects UI elements in the game window (T32).

    Uses fixed layout positions and optional visual detection.
    """

    def __init__(self, layout: str = "fixed_classic"):
        self.layout = layout
        self.element_positions = FIXED_LAYOUT_ELEMENTS.copy()
        self.detected_elements: Dict[UIElement, DetectedElement] = {}

    def detect_elements(
        self,
        window_bounds: Tuple[int, int, int, int],
        image: Optional[Any] = None,
    ) -> Dict[UIElement, DetectedElement]:
        """
        Detect UI elements in the game window.

        Args:
            window_bounds: (x, y, w, h) of the game window
            image: Optional captured image for visual detection

        Returns:
            Dict mapping element type to detected element
        """
        wx, wy, ww, wh = window_bounds
        results = {}

        for element_type, (ex, ey, ew, eh) in self.element_positions.items():
            # Convert relative to absolute coordinates
            abs_bounds = (wx + ex, wy + ey, ew, eh)

            detected = DetectedElement(
                element_type=element_type,
                bounds=abs_bounds,
                confidence=1.0,  # Fixed layout = high confidence
                is_active=False,
            )

            results[element_type] = detected

        self.detected_elements = results
        return results

    def get_element_center(self, element_type: UIElement) -> Optional[Tuple[int, int]]:
        """Get the center point of an element."""
        element = self.detected_elements.get(element_type)
        if not element:
            return None

        x, y, w, h = element.bounds
        return (x + w // 2, y + h // 2)

    def is_point_in_element(
        self,
        point: Tuple[int, int],
        element_type: UIElement,
    ) -> bool:
        """Check if a point is within an element's bounds."""
        element = self.detected_elements.get(element_type)
        if not element:
            return False

        x, y, w, h = element.bounds
        px, py = point

        return x <= px <= x + w and y <= py <= y + h


# =============================================================================
# T33: MINIMAP PARSING FOR REGION INFERENCE
# =============================================================================

@dataclass
class MinimapInfo:
    """Parsed information from the minimap."""
    compass_direction: str = "north"  # N, S, E, W, NE, etc.
    player_dot_position: Tuple[int, int] = (0, 0)
    nearby_dots: List[Tuple[int, int, str]] = field(default_factory=list)  # (x, y, type)
    run_energy: int = 100
    prayer_points: int = 0
    health_percent: float = 1.0
    special_attack_percent: float = 1.0


class MinimapParser:
    """
    Parses the minimap for navigation information (T33).

    Extracts compass direction, player position, and nearby entities.
    """

    # Color ranges for different minimap elements (RGB)
    COLORS = {
        "player_dot": (255, 255, 255),      # White
        "npc_dot": (255, 255, 0),            # Yellow
        "player_other": (255, 255, 255),    # White with different shade
        "tree": (0, 100, 0),                 # Dark green
        "water": (0, 0, 100),                # Blue
        "path": (150, 150, 150),             # Gray
    }

    def __init__(self):
        self.last_parse_time: float = 0.0
        self.cached_info: Optional[MinimapInfo] = None

    def parse(
        self,
        minimap_image: Any,
        use_cache: bool = True,
        cache_ttl: float = 0.1,
    ) -> MinimapInfo:
        """
        Parse the minimap image.

        Args:
            minimap_image: Cropped minimap image
            use_cache: Use cached result if recent
            cache_ttl: Cache time-to-live in seconds

        Returns:
            Parsed minimap information
        """
        now = time.time()

        if use_cache and self.cached_info and (now - self.last_parse_time) < cache_ttl:
            return self.cached_info

        info = MinimapInfo()

        try:
            # Parse compass direction from image
            info.compass_direction = self._detect_compass(minimap_image)

            # Find player dot (center white dot)
            info.player_dot_position = self._find_player_dot(minimap_image)

            # Find nearby dots
            info.nearby_dots = self._find_nearby_dots(minimap_image)

        except Exception as e:
            logger.error(f"Minimap parsing failed: {e}")

        self.cached_info = info
        self.last_parse_time = now

        return info

    def _detect_compass(self, image: Any) -> str:
        """Detect compass direction from minimap."""
        # Simplified: would need actual compass needle detection
        # For now, return north as default
        return "north"

    def _find_player_dot(self, image: Any) -> Tuple[int, int]:
        """Find the player's position dot on minimap."""
        # The player is always at the center of a square minimap
        try:
            import numpy as np
            if hasattr(image, 'shape'):
                h, w = image.shape[:2]
            else:
                w, h = image.size
            return (w // 2, h // 2)
        except Exception:
            return (75, 75)  # Default center for 150x150 minimap

    def _find_nearby_dots(self, image: Any) -> List[Tuple[int, int, str]]:
        """Find nearby entity dots on minimap."""
        dots = []

        try:
            import numpy as np

            if not hasattr(image, 'shape'):
                image = np.array(image)

            # Look for yellow (NPC) and white (player) dots
            # This is simplified - actual implementation would use
            # proper color thresholding

        except Exception as e:
            logger.debug(f"Dot detection skipped: {e}")

        return dots

    def get_direction_to_target(
        self,
        target_dot: Tuple[int, int],
    ) -> str:
        """
        Get compass direction from player to target.

        Args:
            target_dot: (x, y) position of target on minimap

        Returns:
            Direction string (N, S, E, W, NE, NW, SE, SW)
        """
        if not self.cached_info:
            return "unknown"

        px, py = self.cached_info.player_dot_position
        tx, ty = target_dot

        dx = tx - px
        dy = ty - py

        # Determine direction
        if abs(dx) < 10 and abs(dy) < 10:
            return "here"

        if abs(dx) > abs(dy):
            return "east" if dx > 0 else "west"
        else:
            return "south" if dy > 0 else "north"


# =============================================================================
# T34: CURSOR STATE AND HOVER TEXT EXTRACTION
# =============================================================================

class CursorState(Enum):
    """Types of cursor states in OSRS."""
    DEFAULT = "default"
    INTERACT = "interact"      # Yellow click icon
    ATTACK = "attack"          # Red attack icon
    TALK = "talk"              # Chat bubble
    USE = "use"                # Item use cursor
    WALK = "walk"              # Boot/walk cursor
    UNKNOWN = "unknown"


@dataclass
class HoverInfo:
    """Information about what the cursor is hovering over."""
    cursor_state: CursorState = CursorState.DEFAULT
    hover_text: str = ""
    available_actions: List[str] = field(default_factory=list)
    target_type: str = ""  # "npc", "object", "item", "player", ""
    target_name: str = ""


class CursorTracker:
    """
    Tracks cursor state and hover text (T34).

    Monitors what the player is hovering over.
    """

    # Keywords that indicate cursor types
    CURSOR_KEYWORDS = {
        CursorState.ATTACK: ["attack", "kill", "fight"],
        CursorState.TALK: ["talk-to", "talk to", "speak"],
        CursorState.USE: ["use", "cast", "wield", "wear", "equip"],
        CursorState.INTERACT: ["examine", "take", "pick", "open", "close", "chop", "mine", "fish"],
    }

    def __init__(self):
        self.current_hover: HoverInfo = HoverInfo()
        self.hover_history: List[HoverInfo] = []
        self.last_update: float = 0.0

    def update(self, snapshot: Dict[str, Any]) -> HoverInfo:
        """
        Update hover info from snapshot.

        Args:
            snapshot: Current game snapshot

        Returns:
            Updated HoverInfo
        """
        ui = snapshot.get("ui", {})
        hover_text = ui.get("hover_text", "")

        info = HoverInfo(hover_text=hover_text)

        if hover_text:
            # Parse actions from hover text
            info.available_actions = self._parse_actions(hover_text)

            # Determine cursor state
            info.cursor_state = self._determine_cursor_state(hover_text)

            # Extract target info
            info.target_type, info.target_name = self._extract_target(hover_text)

        self.current_hover = info
        self.hover_history.append(info)
        if len(self.hover_history) > 100:
            self.hover_history.pop(0)

        self.last_update = time.time()
        return info

    def _parse_actions(self, hover_text: str) -> List[str]:
        """Parse available actions from hover text."""
        # OSRS format: "Action1 / Action2 / Action3 TargetName"
        actions = []

        if "/" in hover_text:
            parts = hover_text.split("/")
            for part in parts:
                action = part.strip().split()[0] if part.strip() else ""
                if action:
                    actions.append(action)
        else:
            # Single action
            parts = hover_text.strip().split()
            if parts:
                actions.append(parts[0])

        return actions

    def _determine_cursor_state(self, hover_text: str) -> CursorState:
        """Determine cursor state from hover text."""
        hover_lower = hover_text.lower()

        for state, keywords in self.CURSOR_KEYWORDS.items():
            if any(kw in hover_lower for kw in keywords):
                return state

        if hover_text:
            return CursorState.INTERACT

        return CursorState.DEFAULT

    def _extract_target(self, hover_text: str) -> Tuple[str, str]:
        """Extract target type and name from hover text."""
        # Remove action prefix to get target
        parts = hover_text.split()
        if len(parts) < 2:
            return "", ""

        # First word is usually the action
        target_parts = parts[1:]
        target_name = " ".join(target_parts)

        # Determine target type based on keywords
        target_lower = target_name.lower()

        if any(kw in target_lower for kw in ["npc", "man", "woman", "guard", "wizard"]):
            return "npc", target_name
        if any(kw in target_lower for kw in ["tree", "rock", "door", "gate", "ladder"]):
            return "object", target_name
        if any(kw in target_lower for kw in ["sword", "axe", "food", "potion"]):
            return "item", target_name

        return "", target_name

    def get_default_action(self) -> str:
        """Get the default (left-click) action."""
        if self.current_hover.available_actions:
            return self.current_hover.available_actions[0]
        return ""

    def has_action(self, action: str) -> bool:
        """Check if a specific action is available."""
        action_lower = action.lower()
        return any(
            action_lower in a.lower()
            for a in self.current_hover.available_actions
        )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # T28: Window tracking
    "WindowInfo",
    "WindowTracker",

    # T29: Screen capture
    "CaptureConfig",
    "CapturedFrame",
    "ScreenCapture",

    # T30: Metrics
    "CaptureMetrics",
    "MetricsTracker",

    # T31: OCR
    "OCRProvider",
    "TesseractProvider",
    "EasyOCRProvider",
    "NoopProvider",
    "OCRManager",

    # T32: UI detection
    "UIElement",
    "DetectedElement",
    "UIDetector",

    # T33: Minimap parsing
    "MinimapInfo",
    "MinimapParser",

    # T34: Cursor tracking
    "CursorState",
    "HoverInfo",
    "CursorTracker",
]
