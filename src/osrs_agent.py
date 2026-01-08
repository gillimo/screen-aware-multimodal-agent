"""
OSRS Agent - General purpose agent that plays RuneScape.

Architecture:
1. Perception: Capture screen, identify elements (ML classifier + icon cache)
2. Decision: Local model analyzes state and chooses action
3. Execution: Execute the action using sidebar/input functions
"""
import ctypes
import ctypes.wintypes
import time
import json
from pathlib import Path
from PIL import ImageGrab, Image
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass

from src.input_exec import move_mouse_path, click, press_key_name
from src.osrs_sidebar import (
    click_tab, open_inventory, get_window_offset,
    click_inventory_slot, click_minimap, click_compass, toggle_run,
    TOP_TABS, BOTTOM_TABS, get_inventory_slot_pos,
)
from src.icon_recognition import (
    get_icon_cache, identify_active_tab, is_highlighted,
    capture_sidebar_icons, extract_icon_from_screen,
)
from src.local_model import run_local_model
from src.game_actions import (
    press_dialogue_continue, press_dialogue_option,
    get_chat_logger, log_chat,
)


@dataclass
class GameState:
    """Current game state from perception."""
    screenshot: Optional[Image.Image] = None
    window_offset: Tuple[int, int] = (0, 0)
    active_tab: Optional[str] = None
    hover_text: str = ""
    chat_text: str = ""
    player_idle: bool = True
    inventory_open: bool = False


class OSRSAgent:
    """
    General purpose OSRS agent.
    """

    def __init__(self):
        self.state = GameState()
        self.chat_logger = get_chat_logger()
        self.icon_cache = get_icon_cache()
        self.tick_count = 0
        self.last_action = None

    def focus_game(self) -> bool:
        """Focus the RuneLite window."""
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
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            time.sleep(0.2)
            return True
        return False

    def perceive(self) -> GameState:
        """
        Capture and analyze the current game state.
        """
        # Get window offset
        self.state.window_offset = get_window_offset()

        # Capture screenshot
        self.state.screenshot = ImageGrab.grab()

        # Identify active sidebar tab
        self.state.active_tab = identify_active_tab(
            self.state.screenshot,
            self.state.window_offset
        )

        # Check if inventory is the active tab
        self.state.inventory_open = (self.state.active_tab == "inventory")

        return self.state

    def build_prompt(self) -> str:
        """Build prompt for the local model."""
        prompt = f"""You are an OSRS agent. Analyze the game state and choose ONE action.

CURRENT STATE:
- Active tab: {self.state.active_tab or "unknown"}
- Inventory open: {self.state.inventory_open}
- Last action: {self.last_action}
- Tick: {self.tick_count}

AVAILABLE ACTIONS:
- CLICK_TAB <name>: Click sidebar tab (inventory, equipment, prayer, magic, skills, combat, settings)
- CLICK_SLOT <0-27>: Click inventory slot
- CLICK <x> <y>: Click at screen coordinates
- SPACEBAR: Continue dialogue
- NUMBER <1-5>: Select dialogue option
- MINIMAP <dx> <dy>: Click minimap at offset from center
- WAIT: Do nothing

RULES:
1. If dialogue is showing, use SPACEBAR or NUMBER to respond
2. If you need to use an item, first CLICK_TAB inventory, then CLICK_SLOT
3. Look for highlighted/glowing objects to interact with
4. Yellow arrows point to objectives

Output ONLY the action command, nothing else.
Example: CLICK_TAB inventory
Example: CLICK 450 300
Example: SPACEBAR
"""
        return prompt

    def parse_action(self, response: str) -> Tuple[str, Any]:
        """Parse model response into action type and data."""
        response = response.strip().upper()
        parts = response.split()

        if not parts:
            return ("wait", None)

        cmd = parts[0]

        if cmd == "CLICK_TAB" and len(parts) > 1:
            return ("click_tab", parts[1].lower())

        if cmd == "CLICK_SLOT" and len(parts) > 1:
            try:
                slot = int(parts[1])
                return ("click_slot", slot)
            except:
                return ("wait", None)

        if cmd == "CLICK" and len(parts) >= 3:
            try:
                x, y = int(parts[1]), int(parts[2])
                return ("click", (x, y))
            except:
                return ("wait", None)

        if cmd == "SPACEBAR" or cmd == "SPACE":
            return ("spacebar", None)

        if cmd == "NUMBER" and len(parts) > 1:
            try:
                num = int(parts[1])
                return ("number", num)
            except:
                return ("number", 1)

        if cmd == "MINIMAP" and len(parts) >= 3:
            try:
                dx, dy = int(parts[1]), int(parts[2])
                return ("minimap", (dx, dy))
            except:
                return ("wait", None)

        if cmd == "WAIT":
            return ("wait", None)

        return ("wait", None)

    def execute(self, action_type: str, action_data: Any) -> bool:
        """Execute an action."""
        self.last_action = f"{action_type} {action_data}"
        ox, oy = self.state.window_offset

        if action_type == "click_tab":
            return click_tab(action_data, (ox, oy))

        elif action_type == "click_slot":
            return click_inventory_slot(action_data, (ox, oy))

        elif action_type == "click":
            x, y = action_data
            move_mouse_path(x, y, steps=20)
            time.sleep(0.1)
            click()
            return True

        elif action_type == "spacebar":
            press_dialogue_continue()
            return True

        elif action_type == "number":
            press_dialogue_option(action_data)
            return True

        elif action_type == "minimap":
            dx, dy = action_data
            return click_minimap(dx, dy, (ox, oy))

        elif action_type == "wait":
            time.sleep(0.3)
            return True

        return False

    def tick(self) -> bool:
        """
        Run one agent tick: perceive -> decide -> execute.
        Returns False if agent should stop.
        """
        self.tick_count += 1
        print(f"\n[Tick {self.tick_count}]")

        # 1. Perceive
        self.perceive()
        print(f"  Active tab: {self.state.active_tab}")

        # Save screenshot for debugging
        if self.state.screenshot:
            self.state.screenshot.save("data/current_screen.png")

        # 2. Decide
        prompt = self.build_prompt()
        print("  Asking model...")

        try:
            response = run_local_model(prompt)
            response = response.strip()
            print(f"  Model: {response[:60]}")
        except Exception as e:
            print(f"  Model error: {e}")
            response = "WAIT"

        # 3. Parse
        action_type, action_data = self.parse_action(response)
        print(f"  Action: {action_type} -> {action_data}")

        # 4. Execute
        success = self.execute(action_type, action_data)
        print(f"  Result: {'OK' if success else 'FAIL'}")

        # Log
        log_chat(f"Tick {self.tick_count}: {action_type} {action_data}", source="agent")

        return True

    def run(self, max_ticks: int = 100, tick_delay: float = 1.5):
        """Run the agent loop."""
        print("=" * 50)
        print("OSRS Agent Starting")
        print("=" * 50)

        if not self.focus_game():
            print("ERROR: Could not find RuneLite window!")
            return

        print(f"Window offset: {get_window_offset()}")
        print(f"Running for {max_ticks} ticks...")
        print("Press Ctrl+C to stop\n")

        try:
            for _ in range(max_ticks):
                if not self.tick():
                    break
                time.sleep(tick_delay)
        except KeyboardInterrupt:
            print("\n\nStopped by user")

        print(f"\nAgent finished after {self.tick_count} ticks")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="OSRS Agent")
    parser.add_argument("--ticks", type=int, default=50, help="Max ticks to run")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between ticks")
    args = parser.parse_args()

    agent = OSRSAgent()
    agent.run(max_ticks=args.ticks, tick_delay=args.delay)


if __name__ == "__main__":
    main()
