"""
OSRS Agent - Main entry point.

For full autonomous agent:
    python run_agent.py --goal "complete tutorial island"

For basic hover scanner (legacy):
    python run_agent.py --mode scanner

Usage examples:
    python run_agent.py --goal "train woodcutting"
    python run_agent.py --goal "talk to NPCs" --max-ticks 100
    python run_agent.py --mode scanner --cycles 50
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def run_autonomous_agent(goal: str, max_ticks: int, model: str):
    """Run the full autonomous agent."""
    from src.autonomous_agent import AutonomousAgent, AgentConfig

    config = AgentConfig(model_name=model)
    agent = AutonomousAgent(config, goal)
    agent.run(max_ticks=max_ticks)


def run_scanner(max_cycles: int):
    """Run the basic hover scanner (legacy mode)."""
    import ctypes
    import numpy as np
    from PIL import ImageGrab

    from src.perception import find_window
    from src.input_exec import move_mouse_path, click

    TICK_MS = 600
    TICKS = 3

    def grab(bounds):
        return ImageGrab.grab(bbox=bounds)

    def check_cyan_hover(img):
        hover = img.crop((3, 45, 350, 75))
        arr = np.array(hover)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        return np.sum((r < 120) & (g > 150) & (b > 150))

    window = find_window('RuneLite')
    if not window:
        print('ERROR: No RuneLite window found')
        return

    user32 = ctypes.windll.user32
    bounds = window.bounds
    win_x, win_y = bounds[0], bounds[1]
    w = bounds[2] - win_x
    h = bounds[3] - win_y

    print(f'OSRS Scanner Started (Legacy Mode)')
    print(f'Window: {w}x{h} at ({win_x},{win_y})')
    print('-' * 40)

    clicks = 0

    for cycle in range(max_cycles):
        start = time.time()
        user32.SetForegroundWindow(window.handle)
        time.sleep(0.02)

        found = False
        for i in range(12):
            x = 300 + (i % 4) * 150
            y = 250 + (i // 4) * 120

            move_mouse_path(win_x + x, win_y + y, steps=5, step_delay_ms=2)
            time.sleep(0.03)

            img = grab(bounds)
            cyan = check_cyan_hover(img)

            if cyan > 60:
                print(f'[{cycle}] FOUND at ({x},{y}) cyan={cyan} - clicking')
                click(button='left', dwell_ms=25)
                clicks += 1
                found = True
                time.sleep(0.5)
                break

        if not found and cycle % 5 == 0:
            print(f'[{cycle}] Scanning... (total clicks: {clicks})')

        elapsed = (time.time() - start) * 1000
        wait = max(0, TICKS * TICK_MS - elapsed)
        time.sleep(wait / 1000)

    print(f'\nScanner finished. Total clicks: {clicks}')


def main():
    parser = argparse.ArgumentParser(
        description="OSRS Agent - Autonomous gameplay",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_agent.py --goal "complete tutorial island"
  python run_agent.py --goal "train fishing" --max-ticks 500
  python run_agent.py --mode scanner --cycles 50
        """
    )

    parser.add_argument("--mode", choices=["agent", "scanner"], default="agent",
                        help="Mode: 'agent' for full AI, 'scanner' for basic hover detection")
    parser.add_argument("--goal", type=str, default="explore and interact",
                        help="Goal for the agent (agent mode only)")
    parser.add_argument("--max-ticks", type=int, default=0,
                        help="Maximum ticks to run (0 = infinite)")
    parser.add_argument("--cycles", type=int, default=50,
                        help="Max cycles (scanner mode only)")
    parser.add_argument("--model", type=str, default="phi3:mini",
                        help="Local model to use (agent mode only)")
    parser.add_argument("--delay", type=int, default=3,
                        help="Startup delay in seconds")

    args = parser.parse_args()

    print(f"Starting in {args.delay} seconds - switch to RuneLite!")
    time.sleep(args.delay)

    if args.mode == "scanner":
        run_scanner(args.cycles)
    else:
        run_autonomous_agent(args.goal, args.max_ticks, args.model)


if __name__ == "__main__":
    main()
