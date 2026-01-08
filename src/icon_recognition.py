"""
Icon Recognition - Cache and identify UI icons.

This module:
1. Captures and caches reference icons
2. Compares screen regions to cached icons
3. Identifies which tab/icon is active (highlighted)
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image
import json
import hashlib
import numpy as np


ICON_CACHE_DIR = Path(__file__).parent.parent / "data" / "icon_cache"
ICON_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def image_hash(img: Image.Image) -> str:
    """Get a hash of an image for comparison."""
    # Resize to standard size for comparison
    small = img.resize((16, 16)).convert("RGB")
    pixels = list(small.getdata())
    return hashlib.md5(str(pixels).encode()).hexdigest()[:12]


def image_similarity(img1: Image.Image, img2: Image.Image) -> float:
    """
    Compare two images and return similarity score (0-1).
    Higher = more similar.
    """
    # Resize both to same size
    size = (24, 24)
    img1 = img1.resize(size).convert("RGB")
    img2 = img2.resize(size).convert("RGB")

    # Convert to numpy arrays
    arr1 = np.array(img1, dtype=np.float32)
    arr2 = np.array(img2, dtype=np.float32)

    # Calculate mean squared error
    mse = np.mean((arr1 - arr2) ** 2)

    # Convert to similarity (0-1, higher is more similar)
    # Max MSE for RGB is 255^2 = 65025
    similarity = 1 - (mse / 65025)
    return max(0, min(1, similarity))


def average_color(img: Image.Image) -> Tuple[int, int, int]:
    """Get average RGB color of an image."""
    img = img.convert("RGB")
    pixels = list(img.getdata())
    r = sum(p[0] for p in pixels) // len(pixels)
    g = sum(p[1] for p in pixels) // len(pixels)
    b = sum(p[2] for p in pixels) // len(pixels)
    return (r, g, b)


def is_highlighted(img: Image.Image) -> bool:
    """
    Check if an icon appears highlighted (red/orange tint = active tab).
    """
    avg = average_color(img)
    r, g, b = avg

    # Highlighted tabs have more red/orange
    # Normal tabs are more gray/brown
    if r > 100 and r > g * 1.2 and r > b * 1.3:
        return True
    return False


class IconCache:
    """
    Cache for UI icons with recognition capabilities.
    """

    def __init__(self, cache_dir: Path = ICON_CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.icons: Dict[str, Image.Image] = {}
        self.metadata: Dict[str, dict] = {}
        self._load_cache()

    def _load_cache(self):
        """Load cached icons from disk."""
        meta_path = self.cache_dir / "metadata.json"
        if meta_path.exists():
            self.metadata = json.loads(meta_path.read_text())

        for icon_file in self.cache_dir.glob("*.png"):
            name = icon_file.stem
            self.icons[name] = Image.open(icon_file)

    def _save_metadata(self):
        """Save metadata to disk."""
        meta_path = self.cache_dir / "metadata.json"
        meta_path.write_text(json.dumps(self.metadata, indent=2))

    def cache_icon(self, name: str, img: Image.Image, category: str = "unknown"):
        """
        Cache an icon image.

        Args:
            name: Unique name for this icon (e.g., "inventory_tab", "bronze_sword")
            img: PIL Image of the icon
            category: Category (tab, item, npc, object, etc.)
        """
        # Save image
        icon_path = self.cache_dir / f"{name}.png"
        img.save(icon_path)

        # Update cache
        self.icons[name] = img
        self.metadata[name] = {
            "category": category,
            "hash": image_hash(img),
            "avg_color": average_color(img),
            "size": img.size,
        }
        self._save_metadata()

    def find_match(self, img: Image.Image, category: Optional[str] = None, threshold: float = 0.85) -> Optional[str]:
        """
        Find the best matching cached icon.

        Args:
            img: Image to match
            category: Only match icons in this category (optional)
            threshold: Minimum similarity score (0-1)

        Returns:
            Name of best matching icon, or None if no match above threshold
        """
        best_match = None
        best_score = threshold

        for name, cached_img in self.icons.items():
            # Filter by category if specified
            if category and self.metadata.get(name, {}).get("category") != category:
                continue

            score = image_similarity(img, cached_img)
            if score > best_score:
                best_score = score
                best_match = name

        return best_match

    def identify_icon(self, img: Image.Image) -> dict:
        """
        Identify an icon and return info about it.

        Returns:
            {
                "name": "inventory_tab" or None,
                "category": "tab" or None,
                "highlighted": True/False,
                "confidence": 0.95,
            }
        """
        result = {
            "name": None,
            "category": None,
            "highlighted": is_highlighted(img),
            "confidence": 0.0,
        }

        # Find best match
        best_match = None
        best_score = 0.5  # Minimum threshold

        for name, cached_img in self.icons.items():
            score = image_similarity(img, cached_img)
            if score > best_score:
                best_score = score
                best_match = name

        if best_match:
            result["name"] = best_match
            result["category"] = self.metadata.get(best_match, {}).get("category")
            result["confidence"] = best_score

        return result

    def list_icons(self, category: Optional[str] = None) -> List[str]:
        """List all cached icon names, optionally filtered by category."""
        if category:
            return [n for n, m in self.metadata.items() if m.get("category") == category]
        return list(self.icons.keys())


def extract_icon_from_screen(screenshot: Image.Image, x: int, y: int, width: int = 30, height: int = 30) -> Image.Image:
    """Extract an icon region from a screenshot."""
    return screenshot.crop((x, y, x + width, y + height))


def capture_sidebar_icons(screenshot: Image.Image, window_offset: Tuple[int, int] = (0, 0)) -> Dict[str, Image.Image]:
    """
    Capture all sidebar tab icons from a screenshot.

    Returns dict of {tab_name: icon_image}
    """
    from src.osrs_sidebar import TOP_TABS, BOTTOM_TABS

    icons = {}
    ox, oy = window_offset

    for tab in TOP_TABS + BOTTOM_TABS:
        # Extract 30x30 region centered on tab position
        x = ox + tab.x - 15
        y = oy + tab.y - 15
        icon = extract_icon_from_screen(screenshot, x, y, 30, 30)
        icons[tab.name] = icon

    return icons


def identify_active_tab(screenshot: Image.Image, window_offset: Tuple[int, int] = (0, 0)) -> Optional[str]:
    """
    Identify which sidebar tab is currently active (highlighted).

    Returns tab name or None.
    """
    icons = capture_sidebar_icons(screenshot, window_offset)

    for name, icon in icons.items():
        if is_highlighted(icon):
            return name

    return None


# Global icon cache instance
_cache: Optional[IconCache] = None


def get_icon_cache() -> IconCache:
    """Get the global icon cache."""
    global _cache
    if _cache is None:
        _cache = IconCache()
    return _cache


if __name__ == "__main__":
    print("Icon Recognition System")
    print("=" * 40)

    cache = get_icon_cache()
    print(f"Cached icons: {len(cache.icons)}")

    for name in cache.list_icons():
        meta = cache.metadata.get(name, {})
        print(f"  {name}: {meta.get('category', '?')} - {meta.get('avg_color', '?')}")
