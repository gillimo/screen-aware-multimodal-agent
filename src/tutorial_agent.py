"""
Tutorial Island Agent - Agentic loop that captures, analyzes, decides, acts.
"""
import ctypes
import ctypes.wintypes
import time
import json
from PIL import ImageGrab, Image
from pathlib import Path

from src.input_exec import move_mouse_path, click, press_key_name
from src.game_actions import (
    press_dialogue_continue,
    press_dialogue_option,
    log_chat,
    get_chat_logger,
)
from src.local_model import run_local_model


def focus_runelite():
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
    return hwnd is not None


def capture_screen():
    """Capture the full screen."""
    return ImageGrab.grab()


def save_screenshot(img, path="data/current_screen.png"):
    """Save screenshot for debugging."""
    img.save(path)


def build_context(screenshot_path: str) -> str:
    """Build context string for the model."""
    return f"""You are playing OSRS Tutorial Island. Look at the screenshot and decide ONE action.

Current screenshot saved at: {screenshot_path}

AVAILABLE ACTIONS:
- SPACEBAR: Continue dialogue
- NUMBER 1-5: Select dialogue option
- CLICK x,y: Click at screen coordinates
- FISH: Click on a fishing spot (cyan highlighted in water)
- WAIT: Do nothing this tick

Look at:
1. Any yellow text instructions on screen
2. Chat box messages at bottom
3. Highlighted objects (cyan boxes = clickable)
4. Red highlighted UI tabs = currently active

Output ONLY the action, like:
SPACEBAR
CLICK 400,350
FISH
NUMBER 1
WAIT
"""


def parse_action(response: str) -> tuple:
    """Parse the model's response into an action."""
    response = response.strip().upper()

    if "SPACEBAR" in response or "SPACE" in response:
        return ("spacebar", None)

    if "NUMBER" in response:
        for i in range(1, 6):
            if str(i) in response:
                return ("number", i)
        return ("number", 1)

    if "CLICK" in response:
        # Extract coordinates
        import re
        match = re.search(r'(\d+)[,\s]+(\d+)', response)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            return ("click", (x, y))

    if "FISH" in response:
        return ("fish", None)

    if "WAIT" in response:
        return ("wait", None)

    return ("wait", None)


def execute_action(action_type: str, action_data):
    """Execute the parsed action."""
    print(f"  Executing: {action_type} {action_data}")

    if action_type == "spacebar":
        press_key_name("SPACE", hold_ms=50)
        time.sleep(0.2)

    elif action_type == "number":
        press_key_name(str(action_data), hold_ms=50)
        time.sleep(0.2)

    elif action_type == "click":
        x, y = action_data
        move_mouse_path(x, y, steps=20)
        time.sleep(0.1)
        click()
        time.sleep(0.2)

    elif action_type == "fish":
        # Click on approximate fishing spot location
        # Fishing spots are in the pond area - around x=550, y=400 based on screenshots
        move_mouse_path(550, 380, steps=20)
        time.sleep(0.1)
        click()
        time.sleep(0.3)

    elif action_type == "wait":
        time.sleep(0.5)


def run_agent(max_iterations=100, tick_delay=1.0):
    """Main agent loop."""
    print("=" * 50)
    print("Tutorial Island Agent Starting")
    print("=" * 50)

    # Focus game
    if not focus_runelite():
        print("ERROR: Could not find RuneLite window!")
        return

    print("RuneLite focused. Starting agent loop...")
    print("Press Ctrl+C to stop\n")

    for i in range(max_iterations):
        try:
            print(f"\n[Tick {i+1}]")

            # 1. Capture screen
            screenshot = capture_screen()
            save_screenshot(screenshot)
            print(f"  Captured: {screenshot.size}")

            # 2. Build context for model
            context = build_context("data/current_screen.png")

            # 3. Ask model for action
            print("  Asking model...")
            response = run_local_model(context)
            print(f"  Model says: {response[:50]}...")

            # 4. Parse action
            action_type, action_data = parse_action(response)
            print(f"  Parsed: {action_type} -> {action_data}")

            # 5. Execute action
            execute_action(action_type, action_data)

            # 6. Log for debugging
            log_chat(f"Tick {i+1}: {action_type} {action_data}", source="agent")

            # Wait before next tick
            time.sleep(tick_delay)

        except KeyboardInterrupt:
            print("\n\nStopped by user")
            break
        except Exception as e:
            print(f"  ERROR: {e}")
            time.sleep(1)

    print("\nAgent finished.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=int, default=50)
    parser.add_argument("--delay", type=float, default=1.5)
    args = parser.parse_args()

    run_agent(max_iterations=args.ticks, tick_delay=args.delay)
