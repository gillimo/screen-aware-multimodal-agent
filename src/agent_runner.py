"""
OSRS Agent Runner - Continuous gameplay loop using local model for decisions.
"""
import json
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
sys.path.insert(0, str(ROOT))

from src.perception import find_window
from src.fast_perception import perceive
from src.local_model import build_decision_prompt, run_local_model, load_config
from src.model_output import validate_planner_output
from src.humanization import get_active_profile
from src.input_exec import move_mouse_path, click


def save_snapshot(snapshot, path):
    path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


def parse_model_response(response):
    """Extract JSON from model response, handling markdown code blocks."""
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def run_agent(window_title="RuneLite", max_iterations=50, sleep_between=2.0):
    """Main agent loop - capture, decide, act, repeat."""
    print(f"Starting OSRS agent (max {max_iterations} iterations)")
    print(f"Looking for window: {window_title}")

    profile = get_active_profile()
    if not profile:
        print("Warning: No active humanization profile set")

    state = {
        "account": {"name": "Agent"},
        "goals": {
            "short": ["Complete current objective"],
            "mid": ["Progress through game"],
            "long": ["Master the game"]
        }
    }

    for iteration in range(max_iterations):
        print(f"\n=== Iteration {iteration + 1}/{max_iterations} ===")

        # 1. Find game window
        window = find_window(window_title)
        if not window:
            print(f"No window found matching: {window_title}")
            time.sleep(sleep_between)
            continue
        safe_title = window.title.encode('ascii', 'replace').decode('ascii')
        print(f"Found window: {safe_title}")

        # Get window bounds (x, y, w, h)
        bounds = window.bounds  # (left, top, right, bottom)
        x, y, right, bottom = bounds
        w = right - x
        h = bottom - y

        # 2. Capture and analyze screen
        print(f"Capturing screen at ({x}, {y}, {w}, {h})...")
        try:
            result = perceive(window_bounds=(x, y, w, h))
            snapshot = result.to_dict()

            snapshot_path = DATA_DIR / "snapshots" / "snapshot_latest.json"
            save_snapshot(snapshot, snapshot_path)
            print(f"Snapshot saved ({result.total_ms}ms)")

            # Show what we detected
            if result.arrow_position:
                print(f"  Arrow detected at {result.arrow_position} ({result.arrow_confidence:.0%})")
            if result.highlight_position:
                print(f"  Highlight at {result.highlight_position}")
            if result.npcs_on_screen:
                print(f"  {len(result.npcs_on_screen)} NPCs on screen")

        except Exception as e:
            print(f"Perception error: {e}")
            time.sleep(sleep_between)
            continue

        # 3. Ask local model what to do
        print("Querying local model...")
        context_msg = "Look at the game state and decide the next action."
        prompt = build_decision_prompt(state, context_msg, snapshot=snapshot)

        response = run_local_model(prompt, timeout_s=30)
        print(f"Model response: {response[:200]}..." if len(response) > 200 else f"Model response: {response}")

        # 4. Parse decision (skip strict validation for local model)
        decision = parse_model_response(response)
        if not decision:
            print("Could not parse model response as JSON")
            time.sleep(sleep_between)
            continue

        # 5. Execute decision - accept simpler local model format
        action = decision.get("action", "wait")
        target = decision.get("target", {})
        confidence = decision.get("confidence", 0)
        reasoning = decision.get("reasoning", "")

        print(f"Decision: {action} at {target} (confidence: {confidence})")
        print(f"Reasoning: {reasoning}")

        if action == "wait":
            print("Waiting...")
        elif action in ("click", "right_click", "look"):
            tx, ty = target.get("x", 0), target.get("y", 0)
            if tx > 0 and ty > 0:
                # Convert relative coords to absolute screen coords
                abs_x = x + tx
                abs_y = y + ty
                print(f"Moving mouse to ({abs_x}, {abs_y})...")
                move_mouse_path(abs_x, abs_y, steps=25, curve_strength=0.2, jitter_px=1.5, step_delay_ms=8)
                if action != "look":
                    time.sleep(0.1)
                    button = "right" if action == "right_click" else "left"
                    click(button=button, dwell_ms=50)
                    print(f"Clicked {button} at ({abs_x}, {abs_y})")
        else:
            print(f"Action not yet implemented: {action}")

        # 6. Wait before next iteration
        time.sleep(sleep_between)

    print("\nAgent loop complete")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OSRS Agent Runner")
    parser.add_argument("--title", default="RuneLite", help="Window title to find")
    parser.add_argument("--max", type=int, default=50, help="Max iterations")
    parser.add_argument("--sleep", type=float, default=2.0, help="Sleep between iterations")
    args = parser.parse_args()

    run_agent(args.title, args.max, args.sleep)
