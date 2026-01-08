"""Fast perception layer - uses Rust when available, falls back to Python.

This is the main entry point for perception. It combines:
- RuneLite data (structured game state)
- Rust capture/detection (fast pixel analysis)
- Python fallback (when Rust not built)
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Try to import Rust module
try:
    import osrs_core
    HAS_RUST = True
except ImportError:
    HAS_RUST = False

from src import runelite_data


@dataclass
class PerceptionResult:
    """Combined perception result from all sources."""
    # RuneLite data (structured)
    runelite_fresh: bool = False
    player_position: Optional[Tuple[int, int]] = None  # screen coords
    player_world: Optional[Tuple[int, int, int]] = None  # world coords
    camera_direction: str = "unknown"
    npcs_on_screen: list = None
    tutorial_progress: int = 0
    inventory_count: int = 0

    # Detection results (pixel analysis)
    arrow_position: Optional[Tuple[int, int]] = None
    arrow_confidence: float = 0.0
    highlight_position: Optional[Tuple[int, int]] = None
    highlight_confidence: float = 0.0

    # Timing
    capture_ms: int = 0
    detect_ms: int = 0
    total_ms: int = 0

    def __post_init__(self):
        if self.npcs_on_screen is None:
            self.npcs_on_screen = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "runelite_fresh": self.runelite_fresh,
            "player_position": self.player_position,
            "player_world": self.player_world,
            "camera_direction": self.camera_direction,
            "npcs_on_screen": self.npcs_on_screen,
            "tutorial_progress": self.tutorial_progress,
            "inventory_count": self.inventory_count,
            "arrow_position": self.arrow_position,
            "arrow_confidence": self.arrow_confidence,
            "highlight_position": self.highlight_position,
            "highlight_confidence": self.highlight_confidence,
            "capture_ms": self.capture_ms,
            "detect_ms": self.detect_ms,
            "total_ms": self.total_ms,
        }

    def best_target(self) -> Optional[Tuple[int, int]]:
        """Get the best click target based on available data."""
        # Priority: NPC on screen > arrow > highlight
        if self.npcs_on_screen:
            # Return first NPC with screen coords
            for npc in self.npcs_on_screen:
                if npc.get("x") and npc.get("y"):
                    return (npc["x"], npc["y"])

        if self.arrow_position and self.arrow_confidence > 0.3:
            return self.arrow_position

        if self.highlight_position and self.highlight_confidence > 0.3:
            return self.highlight_position

        return None


def perceive(
    window_bounds: Optional[Tuple[int, int, int, int]] = None,
    use_rust: bool = True,
    use_runelite: bool = True,
) -> PerceptionResult:
    """
    Get complete perception of game state.

    Args:
        window_bounds: (x, y, width, height) for screen capture
        use_rust: Try Rust capture/detection if available
        use_runelite: Read RuneLite exported data

    Returns:
        PerceptionResult with all available data
    """
    start_time = time.time()
    result = PerceptionResult()

    # 1. Get RuneLite data (fast, structured)
    if use_runelite:
        rl_data = runelite_data.read_export()
        if rl_data and runelite_data.is_data_fresh():
            result.runelite_fresh = True
            result.tutorial_progress = rl_data.get("tutorial_progress", 0)

            player = rl_data.get("player", {})
            if player:
                sx, sy = player.get("screen_x"), player.get("screen_y")
                if sx is not None and sy is not None:
                    result.player_position = (sx, sy)

                wx = player.get("world_x")
                wy = player.get("world_y")
                wz = player.get("plane", 0)
                if wx is not None and wy is not None:
                    result.player_world = (wx, wy, wz)

            camera = rl_data.get("camera", {})
            result.camera_direction = camera.get("compass_direction", "unknown")

            # NPCs on screen
            for npc in rl_data.get("npcs", []):
                if npc.get("on_screen") and npc.get("screen_x") and npc.get("screen_y"):
                    result.npcs_on_screen.append({
                        "name": npc.get("name"),
                        "x": npc.get("screen_x"),
                        "y": npc.get("screen_y"),
                        "id": npc.get("id"),
                    })

            result.inventory_count = len(rl_data.get("inventory", []))

    # 2. Screen capture and detection (if bounds provided)
    if window_bounds:
        x, y, w, h = window_bounds

        if use_rust and HAS_RUST:
            # Fast Rust path
            try:
                detect_result = osrs_core.capture_and_detect(x, y, w, h)
                data = json.loads(detect_result)

                result.capture_ms = data.get("capture_ms", 0)
                result.detect_ms = data.get("detect_ms", 0)

                if data.get("arrow"):
                    arrow = data["arrow"]
                    result.arrow_position = (arrow["x"], arrow["y"])
                    result.arrow_confidence = arrow.get("confidence", 0.5)

                if data.get("highlight"):
                    hl = data["highlight"]
                    result.highlight_position = (hl["x"], hl["y"])
                    result.highlight_confidence = hl.get("confidence", 0.5)

            except Exception as e:
                # Fall back to Python
                _python_detect(result, x, y, w, h)
        else:
            # Python fallback
            _python_detect(result, x, y, w, h)

    result.total_ms = int((time.time() - start_time) * 1000)
    return result


def _python_detect(result: PerceptionResult, x: int, y: int, w: int, h: int):
    """Python fallback for detection when Rust not available."""
    try:
        from src.perception import capture_frame
        from src.arrow_detector import find_arrow_target
        from PIL import Image

        capture_start = time.time()
        frame = capture_frame((x, y, x + w, y + h))
        result.capture_ms = int((time.time() - capture_start) * 1000)

        img = frame.get("image")
        if img:
            if hasattr(img, 'rgb'):
                pil_img = Image.frombytes('RGB', img.size, img.rgb)
            else:
                pil_img = img

            detect_start = time.time()

            # Arrow detection
            arrow_result = find_arrow_target(pil_img)
            if arrow_result.get("found"):
                result.arrow_position = (arrow_result["x"], arrow_result["y"])
                result.arrow_confidence = arrow_result.get("confidence", 0.5)

            result.detect_ms = int((time.time() - detect_start) * 1000)

    except Exception:
        pass


def find_npc(name: str) -> Optional[Tuple[int, int]]:
    """Quick lookup: find NPC screen position by name."""
    coords = runelite_data.find_npc_on_screen(name)
    return coords


def get_tutorial_phase() -> str:
    """Quick lookup: current tutorial phase."""
    return runelite_data.get_tutorial_phase()


def is_player_idle() -> bool:
    """Quick lookup: is player idle?"""
    return runelite_data.is_player_idle()


# Check Rust availability
def rust_available() -> bool:
    return HAS_RUST


def capture_snapshot(
    window_bounds: Optional[Tuple[int, int, int, int]] = None,
) -> Dict[str, Any]:
    """
    Capture a game snapshot with OCR using existing infrastructure.
    """
    from pathlib import Path
    from src.perception import capture_frame
    from src.ocr import run_ocr

    ROOT = Path(__file__).resolve().parents[1]
    DATA_DIR = ROOT / "data"

    result = perceive(window_bounds=window_bounds)

    # Default snapshot structure
    snapshot = {
        "player": {
            "x": result.player_world[0] if result.player_world else 0,
            "y": result.player_world[1] if result.player_world else 0,
            "plane": result.player_world[2] if result.player_world else 0,
            "screen_x": result.player_position[0] if result.player_position else 0,
            "screen_y": result.player_position[1] if result.player_position else 0,
        },
        "ui": {
            "hover_text": "",
            "dialogue_options": [],
            "open_interface": "none",
            "inventory": [],
            "tabs": {},
        },
        "npcs": result.npcs_on_screen,
        "objects": [],
        "ocr": [],
        "camera": {
            "direction": result.camera_direction,
        },
        "meta": {
            "tutorial_progress": result.tutorial_progress,
            "inventory_count": result.inventory_count,
            "runelite_fresh": result.runelite_fresh,
            "capture_ms": result.capture_ms,
            "detect_ms": result.detect_ms,
            "total_ms": result.total_ms,
        },
    }

    # Run OCR using existing config
    if window_bounds:
        try:
            # Load OCR config
            ocr_config_path = DATA_DIR / "ocr_config.json"
            ocr_regions_path = DATA_DIR / "ocr_regions.json"

            ocr_config = {}
            ocr_regions = {}

            if ocr_config_path.exists():
                ocr_config = json.loads(ocr_config_path.read_text())
            if ocr_regions_path.exists():
                ocr_regions = json.loads(ocr_regions_path.read_text())

            provider = ocr_config.get("provider", "tesseract")

            # Capture frame for OCR
            wx, wy, ww, wh = window_bounds
            frame = capture_frame((wx, wy, ww, wh))
            image = frame.get("image")

            if image and ocr_regions:
                # Prepare regions with image reference
                prepared_regions = {}
                for name, bounds in ocr_regions.items():
                    if isinstance(bounds, dict):
                        prepared_regions[name] = {
                            **bounds,
                            "_image": image,
                        }

                # Run OCR
                ocr_entries = run_ocr(prepared_regions, provider_name=provider, provider_config=ocr_config)

                # Extract results
                for entry in ocr_entries:
                    if entry.region == "hover_text":
                        snapshot["ui"]["hover_text"] = entry.text
                    elif entry.region == "dialogue":
                        snapshot["ui"]["dialogue_options"] = [
                            line for line in entry.text.splitlines() if line.strip()
                        ]

                snapshot["ocr"] = [
                    {"region": e.region, "text": e.text, "confidence": e.confidence}
                    for e in ocr_entries
                ]

        except Exception as e:
            # OCR failed - continue without it
            pass

    # Add arrow/highlight if detected
    if result.arrow_position:
        snapshot["arrow"] = {
            "x": result.arrow_position[0],
            "y": result.arrow_position[1],
            "confidence": result.arrow_confidence,
        }

    if result.highlight_position:
        snapshot["highlight"] = {
            "x": result.highlight_position[0],
            "y": result.highlight_position[1],
            "confidence": result.highlight_confidence,
        }

    return snapshot


if __name__ == "__main__":
    print(f"Rust module available: {HAS_RUST}")
    print("\nTesting perception...")

    result = perceive(use_rust=False)  # Test without Rust first
    print(f"RuneLite fresh: {result.runelite_fresh}")
    print(f"Tutorial progress: {result.tutorial_progress}")
    print(f"NPCs on screen: {len(result.npcs_on_screen)}")
    print(f"Camera direction: {result.camera_direction}")

    if result.npcs_on_screen:
        print(f"First NPC: {result.npcs_on_screen[0]}")

    print(f"\nTotal time: {result.total_ms}ms")
