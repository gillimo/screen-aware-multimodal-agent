"""Read game data exported by RuneLite plugin or RSProx packet proxy."""
from __future__ import annotations

import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Use orjson for ~10x faster JSON parsing (Rust-based)
try:
    import orjson
    def _json_loads(s): return or_json_loads(s)
    def _json_dumps(obj): return or_json_dumps(obj).decode("utf-8")
except ImportError:
    import json
    def _json_loads(s): return _json_loads(s)
    def _json_dumps(obj): return _json_dumps(obj)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
# Session Stats plugin exports to .runelite folder
EXPORT_PATH = Path.home() / ".runelite" / "session_stats.json"
FALLBACK_PATH = DATA_DIR / "runelite_export.json"

# RSProx HTTP API (packet proxy - preferred source)
RSPROX_HOST = "http://localhost:8081"
RSPROX_TIMEOUT = 0.5  # 500ms timeout for HTTP requests

# Data source preference: rsprox first, then file
_use_rsprox = True
_rsprox_available = None  # None = unknown, True/False = cached check
_last_rsprox_check = 0
RSPROX_CHECK_INTERVAL = 5.0  # Re-check RSProx availability every 5 seconds


def _check_rsprox_available() -> bool:
    """Check if RSProx API is available."""
    global _rsprox_available, _last_rsprox_check
    now = time.time()
    if _rsprox_available is not None and (now - _last_rsprox_check) < RSPROX_CHECK_INTERVAL:
        return _rsprox_available
    try:
        req = urllib.request.Request(f"{RSPROX_HOST}/status", method="GET")
        with urllib.request.urlopen(req, timeout=RSPROX_TIMEOUT) as resp:
            data = _json_loads(resp.read().decode("utf-8"))
            _rsprox_available = data.get("active", False)
    except Exception:
        _rsprox_available = False
    _last_rsprox_check = now
    return _rsprox_available


def _fetch_rsprox(endpoint: str) -> Optional[Dict[str, Any]]:
    """Fetch data from RSProx HTTP API."""
    if not _use_rsprox:
        return None
    try:
        req = urllib.request.Request(f"{RSPROX_HOST}{endpoint}", method="GET")
        with urllib.request.urlopen(req, timeout=RSPROX_TIMEOUT) as resp:
            data = _json_loads(resp.read().decode("utf-8"))
            if "error" in data:
                return None
            return data
    except Exception:
        return None


def _rsprox_to_normalized(rsprox_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert RSProx /gamestate response to our normalized format."""
    data = {}
    data["timestamp"] = rsprox_data.get("timestamp", int(time.time() * 1000))
    data["game_tick"] = rsprox_data.get("tick", 0)
    data["source"] = "rsprox"

    # Player data
    p = rsprox_data.get("player")
    if p:
        coord = p.get("coord", {})
        data["player"] = {
            "world_x": coord.get("x"),
            "world_y": coord.get("z"),  # RSProx uses z for y
            "plane": coord.get("level", 0),
            "screen_x": None,  # RSProx doesn't have screen coords
            "screen_y": None,
            "animation": -1,  # TODO: Add animation tracking to RSProx
            "name": p.get("name"),
        }

    # NPCs
    npcs = rsprox_data.get("npcs", [])
    data["npcs"] = []
    for npc in npcs:
        coord = npc.get("coord", {})
        data["npcs"].append({
            "id": npc.get("id"),
            "name": npc.get("name"),
            "world_x": coord.get("x"),
            "world_y": coord.get("z"),
            "screen_x": None,  # Not available from packets
            "screen_y": None,
            "on_screen": True,  # If RSProx sees it, it's nearby
            "angle": npc.get("angle"),
        })

    # Skills and tutorial progress need separate fetch
    data["skills"] = {}
    data["inventory"] = []
    data["tutorial_progress"] = 0

    return data


def set_rsprox_enabled(enabled: bool):
    """Enable or disable RSProx as data source."""
    global _use_rsprox
    _use_rsprox = enabled


def is_rsprox_connected() -> bool:
    """Check if RSProx is connected and has an active session."""
    return _check_rsprox_available()


def read_export() -> Optional[Dict[str, Any]]:
    """Read game data from RSProx (preferred) or file fallback."""
    # Try RSProx first (packet proxy - most accurate)
    if _use_rsprox and _check_rsprox_available():
        rsprox_data = _fetch_rsprox("/gamestate")
        if rsprox_data:
            return _rsprox_to_normalized(rsprox_data)

    # Fallback to file-based export
    for path in [EXPORT_PATH, FALLBACK_PATH]:
        if path.exists():
            try:
                raw = _json_loads(path.read_text(encoding="utf-8"))
                # Normalize short field names from Session Stats plugin
                return _normalize_export(raw)
            except Exception:
                continue
    return None


def _normalize_export(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize short field names to full names."""
    # Session Stats uses short names to reduce file size
    # t -> timestamp, p -> player, c -> camera, etc.
    data = {}
    data["timestamp"] = raw.get("t", raw.get("timestamp", 0))
    data["game_tick"] = raw.get("tick", raw.get("game_tick", 0))

    # Player data
    p = raw.get("p", raw.get("player", {}))
    if p:
        data["player"] = {
            "world_x": p.get("wx", p.get("world_x")),
            "world_y": p.get("wy", p.get("world_y")),
            "plane": p.get("wz", p.get("plane", 0)),
            "screen_x": p.get("sx", p.get("screen_x")),
            "screen_y": p.get("sy", p.get("screen_y")),
            "animation": p.get("a", p.get("animation", -1)),
        }

    # Camera
    c = raw.get("c", raw.get("camera", {}))
    if c:
        yaw = c.get("y", c.get("yaw", 0))
        data["camera"] = {
            "yaw": yaw,
            "pitch": c.get("p", c.get("pitch", 0)),
            "compass_direction": _yaw_to_direction(yaw),
        }

    # NPCs
    npcs = raw.get("npcs", [])
    data["npcs"] = []
    for npc in npcs:
        data["npcs"].append({
            "id": npc.get("id"),
            "name": npc.get("n", npc.get("name")),
            "world_x": npc.get("wx", npc.get("world_x")),
            "world_y": npc.get("wy", npc.get("world_y")),
            "screen_x": npc.get("sx", npc.get("screen_x")),
            "screen_y": npc.get("sy", npc.get("screen_y")),
            "on_screen": npc.get("v", npc.get("on_screen", False)),
        })

    # Inventory
    inv = raw.get("inv", raw.get("inventory", []))
    data["inventory"] = []
    for item in inv:
        data["inventory"].append({
            "slot": item.get("s", item.get("slot")),
            "id": item.get("id"),
            "quantity": item.get("q", item.get("quantity", 1)),
        })

    # Skills (already short)
    data["skills"] = raw.get("sk", raw.get("skills", {}))

    # Tutorial progress
    data["tutorial_progress"] = raw.get("tp", raw.get("tutorial_progress", 0))

    return data


def _yaw_to_direction(yaw: int) -> str:
    """Convert camera yaw to compass direction."""
    # RuneLite: 0=south, 512=west, 1024=north, 1536=east
    normalized = (yaw + 128) % 2048
    sector = normalized // 256
    directions = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
    return directions[sector] if sector < 8 else "N"


def is_data_fresh(max_age_ms: int = 3000) -> bool:
    """Check if export data is recent enough."""
    data = read_export()
    if not data:
        return False
    timestamp = data.get("timestamp", 0)
    age_ms = int(time.time() * 1000) - timestamp
    return age_ms < max_age_ms


def get_player_position() -> Optional[Dict[str, int]]:
    """Get player's world and screen position."""
    data = read_export()
    if not data:
        return None
    return data.get("player")


def get_camera() -> Optional[Dict[str, Any]]:
    """Get camera orientation."""
    data = read_export()
    if not data:
        return None
    return data.get("camera")


def get_compass_direction() -> str:
    """Get camera compass direction (N, S, E, W, etc)."""
    camera = get_camera()
    if not camera:
        return "unknown"
    return camera.get("compass_direction", "unknown")


def get_npcs() -> List[Dict[str, Any]]:
    """Get list of nearby NPCs."""
    data = read_export()
    if not data:
        return []
    return data.get("npcs", [])


def find_npc_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Find an NPC by name (case-insensitive partial match)."""
    npcs = get_npcs()
    name_lower = name.lower()
    for npc in npcs:
        npc_name = npc.get("name", "")
        if npc_name and name_lower in npc_name.lower():
            return npc
    return None


def find_npc_on_screen(name: str) -> Optional[Tuple[int, int]]:
    """Find an NPC by name and return screen coordinates if on screen."""
    npc = find_npc_by_name(name)
    if not npc:
        return None
    if not npc.get("on_screen", False):
        return None
    screen_x = npc.get("screen_x")
    screen_y = npc.get("screen_y")
    if screen_x is None or screen_y is None:
        return None
    return (screen_x, screen_y)


def get_inventory() -> List[Dict[str, Any]]:
    """Get inventory contents."""
    data = read_export()
    if not data:
        return []
    return data.get("inventory", [])


def has_item(item_id: int) -> bool:
    """Check if inventory contains an item by ID."""
    inventory = get_inventory()
    for item in inventory:
        if item.get("id") == item_id:
            return True
    return False


def get_skill_level(skill_name: str) -> int:
    """Get a skill's real level."""
    data = read_export()
    if not data:
        return 0
    skills = data.get("skills", {})
    skill_data = skills.get(skill_name.lower(), {})
    return skill_data.get("level", 0)


def get_tutorial_progress() -> int:
    """Get Tutorial Island progress varbit value."""
    # Try RSProx direct varp endpoint first (fastest)
    if _use_rsprox and _check_rsprox_available():
        varp_data = _fetch_rsprox("/varps")
        if varp_data:
            return varp_data.get("tutorial_progress", 0)

    # Fallback to full export
    data = read_export()
    if not data:
        return 0
    return data.get("tutorial_progress", 0)


def get_player_animation() -> int:
    """Get player's current animation ID (-1 = idle)."""
    player = get_player_position()
    if not player:
        return -1
    return player.get("animation", -1)


def is_player_idle() -> bool:
    """Check if player is idle (no animation)."""
    return get_player_animation() == -1


# Tutorial Island progress mappings
TUTORIAL_PHASES = {
    0: "character_creation",
    10: "talk_to_guide",
    20: "settings_tab",
    30: "leave_room",
    70: "survival_expert_talk",
    80: "fishing",
    90: "cooking",
    120: "gate_to_chef",
    130: "chef_talk",
    # ... add more as needed
}


def get_tutorial_phase() -> str:
    """Get current tutorial phase name based on varbit."""
    progress = get_tutorial_progress()
    # Find closest phase
    phase = "unknown"
    for threshold, name in sorted(TUTORIAL_PHASES.items()):
        if progress >= threshold:
            phase = name
    return phase


def build_game_context() -> Dict[str, Any]:
    """Build a context dict suitable for the local model."""
    data = read_export()
    if not data or not is_data_fresh():
        return {"source": "runelite", "fresh": False}

    player = data.get("player", {})
    camera = data.get("camera", {})
    npcs = data.get("npcs", [])
    inventory = data.get("inventory", [])

    # Find key NPCs on screen
    npcs_on_screen = [
        {"name": n.get("name"), "x": n.get("screen_x"), "y": n.get("screen_y")}
        for n in npcs
        if n.get("on_screen") and n.get("screen_x") and n.get("screen_y")
    ]

    return {
        "source": "runelite",
        "fresh": True,
        "player": {
            "world_x": player.get("world_x"),
            "world_y": player.get("world_y"),
            "screen_x": player.get("screen_x"),
            "screen_y": player.get("screen_y"),
            "animation": player.get("animation"),
            "idle": player.get("animation", -1) == -1,
        },
        "camera_direction": camera.get("compass_direction", "unknown"),
        "npcs_on_screen": npcs_on_screen,
        "inventory_count": len(inventory),
        "tutorial_progress": data.get("tutorial_progress", 0),
        "tutorial_phase": get_tutorial_phase(),
    }


if __name__ == "__main__":
    # Test reading data
    import sys

    print("Testing RuneLite data reader...")
    data = read_export()
    if data:
        print(f"Data fresh: {is_data_fresh()}")
        print(f"Player: {get_player_position()}")
        print(f"Camera: {get_compass_direction()}")
        print(f"NPCs: {len(get_npcs())}")
        print(f"Tutorial progress: {get_tutorial_progress()}")
        print(f"Tutorial phase: {get_tutorial_phase()}")

        # Look for Survival Expert
        survival = find_npc_on_screen("Survival")
        if survival:
            print(f"Survival Expert on screen at: {survival}")
        else:
            print("Survival Expert not on screen")

        print("\nFull context:")
        print(_json_dumps(build_game_context(), indent=2))
    else:
        print("No RuneLite export data found.")
        print(f"Expected at: {EXPORT_PATH}")
        print("Make sure the AgentOSRS RuneLite plugin is running.")
