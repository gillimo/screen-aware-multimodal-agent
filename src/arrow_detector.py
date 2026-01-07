"""
DEPRECATED: Arrow detection is not used.

The agent uses hover text and right-click menus for target identification,
not the yellow arrow indicator. This provides more reliable and human-like
interaction patterns.

See src/game_actions.py for the hover-text based approach.
"""
from __future__ import annotations

from typing import Optional, Tuple
from PIL import Image
import numpy as np


def find_yellow_arrow(image: Image.Image) -> Optional[Tuple[int, int]]:
    """
    Find the flashing yellow arrow in OSRS screenshot.
    Returns (x, y) center of arrow if found, None otherwise.

    The arrow is bright yellow (#FFFF00 or similar) and typically
    appears as a downward-pointing indicator.
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    arr = np.array(image)

    # Yellow arrow color range (bright yellow)
    # R: 200-255, G: 200-255, B: 0-80
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    yellow_mask = (
        (r > 200) & (r <= 255) &
        (g > 200) & (g <= 255) &
        (b < 80)
    )

    # Find clusters of yellow pixels (arrow is usually 10-50 pixels)
    yellow_coords = np.argwhere(yellow_mask)

    if len(yellow_coords) < 5:
        return None

    # Find the centroid of yellow pixels
    # Filter to largest cluster if multiple yellows exist
    if len(yellow_coords) > 0:
        y_center = int(np.mean(yellow_coords[:, 0]))
        x_center = int(np.mean(yellow_coords[:, 1]))

        # Verify it's actually an arrow shape (taller than wide, or has point)
        y_coords = yellow_coords[:, 0]
        x_coords = yellow_coords[:, 1]

        height = y_coords.max() - y_coords.min()
        width = x_coords.max() - x_coords.min()

        # Arrow is typically taller than wide or similar dimensions
        if height >= 5 and width >= 5:
            # Return bottom center (tip of arrow pointing down)
            return (x_center, y_coords.max())

    return None


def find_arrow_target(image: Image.Image) -> Optional[dict]:
    """
    Find arrow and return target info for clicking.
    """
    result = find_yellow_arrow(image)
    if result:
        x, y = result
        return {
            "found": True,
            "x": x,
            "y": y,
            "confidence": 0.8,
            "source": "yellow_arrow"
        }
    return {"found": False}
