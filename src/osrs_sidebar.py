"""
OSRS Fixed Classic Sidebar - Universal sidebar handling.

Fixed Classic Layout (765x503 game area):
- Game area: 0,0 to 512,334 (within client)
- Sidebar starts at x=519
- Minimap at top right
- Tab rows below minimap
- Inventory/panel area below tabs
"""
from dataclasses import dataclass
from typing import Optional, Tuple, Dict
from src.input_exec import move_mouse_path, click, press_key_name
import time


# Fixed Classic sidebar coordinates (relative to game client top-left)
# These are the standard OSRS Fixed mode coordinates

@dataclass
class SidebarTab:
    name: str
    x: int  # Center x of tab icon
    y: int  # Center y of tab icon
    hotkey: Optional[str] = None  # F-key if available


# Top row of tabs (below minimap)
TOP_TABS = [
    SidebarTab("combat", 545, 203, "F1"),
    SidebarTab("skills", 578, 203, "F2"),
    SidebarTab("quest", 611, 203, "F3"),
    SidebarTab("inventory", 644, 203, None),  # ESC toggles, no dedicated F-key in classic
    SidebarTab("equipment", 677, 203, "F4"),
    SidebarTab("prayer", 710, 203, "F5"),
    SidebarTab("magic", 743, 203, "F6"),
]

# Bottom row of tabs
BOTTOM_TABS = [
    SidebarTab("clan", 545, 466, "F7"),
    SidebarTab("friends", 578, 466, None),
    SidebarTab("account", 611, 466, None),
    SidebarTab("logout", 644, 466, None),
    SidebarTab("settings", 677, 466, "F10"),
    SidebarTab("emotes", 710, 466, None),
    SidebarTab("music", 743, 466, None),
]

ALL_TABS = {tab.name: tab for tab in TOP_TABS + BOTTOM_TABS}


def get_tab(name: str) -> Optional[SidebarTab]:
    """Get tab by name."""
    return ALL_TABS.get(name.lower())


def click_tab(name: str, window_offset: Tuple[int, int] = (0, 0)) -> bool:
    """
    Click a sidebar tab by name.

    Args:
        name: Tab name (combat, skills, quest, inventory, equipment, prayer, magic,
              clan, friends, account, logout, settings, emotes, music)
        window_offset: (x, y) offset of game window on screen

    Returns:
        True if tab was found and clicked
    """
    tab = get_tab(name)
    if not tab:
        print(f"Unknown tab: {name}")
        return False

    # Use hotkey if available (faster)
    if tab.hotkey:
        press_key_name(tab.hotkey, hold_ms=50)
        time.sleep(0.1)
        return True

    # Otherwise click the tab
    x = window_offset[0] + tab.x
    y = window_offset[1] + tab.y
    move_mouse_path(x, y, steps=15)
    time.sleep(0.1)
    click()
    time.sleep(0.1)
    return True


def open_inventory(window_offset: Tuple[int, int] = (0, 0)) -> bool:
    """Open inventory tab."""
    return click_tab("inventory", window_offset)


def open_equipment(window_offset: Tuple[int, int] = (0, 0)) -> bool:
    """Open equipment tab."""
    return click_tab("equipment", window_offset)


def open_prayer(window_offset: Tuple[int, int] = (0, 0)) -> bool:
    """Open prayer tab."""
    return click_tab("prayer", window_offset)


def open_magic(window_offset: Tuple[int, int] = (0, 0)) -> bool:
    """Open magic tab."""
    return click_tab("magic", window_offset)


def open_skills(window_offset: Tuple[int, int] = (0, 0)) -> bool:
    """Open skills tab."""
    return click_tab("skills", window_offset)


def open_settings(window_offset: Tuple[int, int] = (0, 0)) -> bool:
    """Open settings tab."""
    return click_tab("settings", window_offset)


# Inventory slot positions (28 slots, 4 columns x 7 rows)
INVENTORY_START_X = 563
INVENTORY_START_Y = 228
SLOT_WIDTH = 42
SLOT_HEIGHT = 36


def get_inventory_slot_pos(slot: int, window_offset: Tuple[int, int] = (0, 0)) -> Tuple[int, int]:
    """
    Get screen position of inventory slot (0-27).

    Slots are numbered:
    0  1  2  3
    4  5  6  7
    ...
    24 25 26 27
    """
    if not 0 <= slot <= 27:
        raise ValueError(f"Slot must be 0-27, got {slot}")

    row = slot // 4
    col = slot % 4

    x = window_offset[0] + INVENTORY_START_X + col * SLOT_WIDTH + SLOT_WIDTH // 2
    y = window_offset[1] + INVENTORY_START_Y + row * SLOT_HEIGHT + SLOT_HEIGHT // 2

    return (x, y)


def click_inventory_slot(slot: int, window_offset: Tuple[int, int] = (0, 0)) -> bool:
    """Click an inventory slot (0-27)."""
    try:
        x, y = get_inventory_slot_pos(slot, window_offset)
        move_mouse_path(x, y, steps=15)
        time.sleep(0.1)
        click()
        return True
    except ValueError:
        return False


# Minimap center and click offsets
MINIMAP_CENTER_X = 643
MINIMAP_CENTER_Y = 83
MINIMAP_RADIUS = 70


def click_minimap(dx: int, dy: int, window_offset: Tuple[int, int] = (0, 0)) -> bool:
    """
    Click on minimap at offset from center.

    Args:
        dx: X offset from center (-70 to 70)
        dy: Y offset from center (-70 to 70)
        window_offset: Game window offset
    """
    x = window_offset[0] + MINIMAP_CENTER_X + dx
    y = window_offset[1] + MINIMAP_CENTER_Y + dy

    move_mouse_path(x, y, steps=15)
    time.sleep(0.1)
    click()
    return True


# Compass for camera reset
COMPASS_X = 563
COMPASS_Y = 26


def click_compass(window_offset: Tuple[int, int] = (0, 0)) -> bool:
    """Click compass to reset camera north."""
    x = window_offset[0] + COMPASS_X
    y = window_offset[1] + COMPASS_Y
    move_mouse_path(x, y, steps=15)
    time.sleep(0.1)
    click()
    return True


# Run energy orb
RUN_ORB_X = 563
RUN_ORB_Y = 137


def toggle_run(window_offset: Tuple[int, int] = (0, 0)) -> bool:
    """Toggle run by clicking run orb."""
    x = window_offset[0] + RUN_ORB_X
    y = window_offset[1] + RUN_ORB_Y
    move_mouse_path(x, y, steps=15)
    time.sleep(0.1)
    click()
    return True


# Prayer/HP/Special orbs
HP_ORB = (524, 80)
PRAYER_ORB = (524, 116)
SPECIAL_ORB = (596, 137)


def get_window_offset() -> Tuple[int, int]:
    """
    Get the current RuneLite window offset.
    Returns (0, 0) if window not found.
    """
    import ctypes
    import ctypes.wintypes

    hwnd = None
    def cb(h, l):
        nonlocal hwnd
        buff = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetWindowTextW(h, buff, 256)
        if 'runelite' in buff.value.lower():
            hwnd = h
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))
    ctypes.windll.user32.EnumWindows(WNDENUMPROC(cb), 0)

    if hwnd:
        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        # Account for window border
        return (rect.left + 8, rect.top + 31)

    return (0, 0)


if __name__ == "__main__":
    # Test sidebar functions
    print("OSRS Fixed Classic Sidebar")
    print("=" * 40)

    offset = get_window_offset()
    print(f"Window offset: {offset}")

    print("\nTop tabs:")
    for tab in TOP_TABS:
        print(f"  {tab.name}: ({tab.x}, {tab.y}) hotkey={tab.hotkey}")

    print("\nBottom tabs:")
    for tab in BOTTOM_TABS:
        print(f"  {tab.name}: ({tab.x}, {tab.y}) hotkey={tab.hotkey}")

    print("\nInventory slot 0:", get_inventory_slot_pos(0, offset))
    print("Inventory slot 27:", get_inventory_slot_pos(27, offset))
