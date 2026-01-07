"""Smart target finding - detects targets using multiple methods.

Only walks/rotates camera when target is confirmed NOT on screen.
"""
from __future__ import annotations

import base64
import io
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"


def save_screenshot_with_timestamp(image: Image.Image, prefix: str = "capture") -> Path:
    """Save screenshot with timestamp filename."""
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    filename = f"{prefix}_{timestamp}.png"
    path = SCREENSHOTS_DIR / filename
    image.save(path)
    return path


def image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


class TargetFinder:
    """Find targets using multiple detection methods.

    Detection order:
    1. Yellow arrow detection (Quest Helper)
    2. Cyan highlight detection (Quest Helper)
    3. Claude vision (if configured and arrow/highlight not found)

    Only suggests walking when target is confirmed NOT on screen.
    """

    def __init__(self, use_claude: bool = True, save_screenshots: bool = True):
        self.use_claude = use_claude
        self.save_screenshots = save_screenshots
        self.last_screenshot_path: Optional[Path] = None
        self.last_target: Optional[Dict[str, Any]] = None
        self.failed_attempts: int = 0
        self.max_failed_before_walk = 3

    def find_target(
        self,
        image: Image.Image,
        target_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Find a target in the image.

        Returns dict with:
            - found: bool
            - x, y: click coordinates (if found)
            - source: detection method used
            - confidence: 0-1
            - should_walk: True only if target confirmed not on screen
            - reasoning: explanation
        """
        context = context or {}

        # Save screenshot for debugging
        if self.save_screenshots:
            self.last_screenshot_path = save_screenshot_with_timestamp(image, "find_target")

        # Method 1: Yellow arrow detection
        arrow_result = self._detect_yellow_arrow(image)
        if arrow_result["found"]:
            self.failed_attempts = 0
            return {
                **arrow_result,
                "should_walk": False,
                "reasoning": "Yellow Quest Helper arrow found on screen"
            }

        # Method 2: Cyan highlight detection
        highlight_result = self._detect_cyan_highlight(image)
        if highlight_result["found"]:
            self.failed_attempts = 0
            return {
                **highlight_result,
                "should_walk": False,
                "reasoning": "Cyan Quest Helper highlight found on screen"
            }

        # Method 3: Claude vision (if enabled)
        if self.use_claude:
            claude_result = self._ask_claude(image, target_name, context)
            if claude_result["found"]:
                self.failed_attempts = 0
                return {
                    **claude_result,
                    "should_walk": False,
                    "reasoning": f"Claude identified target: {claude_result.get('target_description', 'unknown')}"
                }

            # Claude says target not visible - increment failed attempts
            self.failed_attempts += 1
        else:
            self.failed_attempts += 1

        # Only suggest walking after multiple failed detection attempts
        should_walk = self.failed_attempts >= self.max_failed_before_walk

        return {
            "found": False,
            "source": "none",
            "confidence": 0.0,
            "should_walk": should_walk,
            "failed_attempts": self.failed_attempts,
            "reasoning": f"Target not detected after {self.failed_attempts} attempts. "
                        + ("Consider rotating camera." if should_walk else "Will retry detection.")
        }

    def _detect_yellow_arrow(self, image: Image.Image) -> Dict[str, Any]:
        """Detect Quest Helper yellow arrow."""
        try:
            from src.arrow_detector import find_arrow_target
            result = find_arrow_target(image)
            if result.get("found"):
                return {
                    "found": True,
                    "x": result["x"],
                    "y": result["y"],
                    "source": "yellow_arrow",
                    "confidence": result.get("confidence", 0.8)
                }
        except Exception as e:
            pass
        return {"found": False, "source": "yellow_arrow"}

    def _detect_cyan_highlight(self, image: Image.Image) -> Dict[str, Any]:
        """Detect Quest Helper cyan/turquoise highlight on NPCs/objects."""
        try:
            import numpy as np

            if image.mode != "RGB":
                image = image.convert("RGB")

            arr = np.array(image)
            r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

            # Cyan/turquoise highlight: low R, high G, high B
            # Quest Helper uses ~(0, 255, 255) for highlights
            cyan_mask = (
                (r < 80) &
                (g > 180) &
                (b > 180)
            )

            cyan_coords = np.argwhere(cyan_mask)

            # Need enough cyan pixels to be a meaningful highlight
            if len(cyan_coords) >= 20:
                y_center = int(np.mean(cyan_coords[:, 0]))
                x_center = int(np.mean(cyan_coords[:, 1]))

                return {
                    "found": True,
                    "x": x_center,
                    "y": y_center,
                    "source": "cyan_highlight",
                    "confidence": 0.7
                }
        except Exception:
            pass
        return {"found": False, "source": "cyan_highlight"}

    def _ask_claude(
        self,
        image: Image.Image,
        target_name: Optional[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ask Claude to find target in screenshot."""
        try:
            from src.librarian_client import ask_librarian

            screenshot_b64 = image_to_base64(image)

            question = "Where should I click to progress?"
            if target_name:
                question = f"Where is the {target_name}? Give me click coordinates."

            answer = ask_librarian(
                question=question,
                screenshot_b64=screenshot_b64,
                context={
                    "phase": context.get("phase", "unknown"),
                    "tutorial_hint": context.get("tutorial_hint", ""),
                    "hover_text": context.get("hover_text", ""),
                    "target_name": target_name or "",
                }
            )

            if answer and answer.get("target"):
                return {
                    "found": True,
                    "x": answer["target"]["x"],
                    "y": answer["target"]["y"],
                    "source": "claude",
                    "confidence": answer.get("confidence", 0.6),
                    "target_description": answer.get("target_description", ""),
                }
        except Exception as e:
            pass

        return {"found": False, "source": "claude"}

    def suggest_camera_rotation(self) -> Dict[str, Any]:
        """Suggest a camera rotation direction to find target.

        Only called when target confirmed not on screen.
        NOT a pattern - just one rotation to check a new angle.
        """
        import random

        # Random rotation direction - no pattern
        direction = random.choice(["left", "right"])
        amount = random.randint(45, 90)

        return {
            "action": "camera_rotate",
            "direction": direction,
            "degrees": amount,
            "reasoning": "Target not visible - checking different camera angle"
        }

    def reset(self):
        """Reset failed attempt counter."""
        self.failed_attempts = 0
        self.last_target = None


def find_target_smart(
    image: Image.Image,
    target_name: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    use_claude: bool = True,
) -> Dict[str, Any]:
    """Convenience function for one-off target finding."""
    finder = TargetFinder(use_claude=use_claude)
    return finder.find_target(image, target_name, context)
