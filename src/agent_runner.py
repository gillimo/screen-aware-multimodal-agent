"""
OSRS Agent Runner - Wrapper for autonomous agent.

This file provides backward compatibility. For the full implementation,
see src/autonomous_agent.py

Usage:
    python -m src.agent_runner --goal "complete tutorial island"
    python -m src.agent_runner --max 100 --sleep 1.8
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.autonomous_agent import AutonomousAgent, AgentConfig, main

# Re-export for backward compatibility
__all__ = ['AutonomousAgent', 'AgentConfig', 'run_agent']


def run_agent(window_title="RuneLite", max_iterations=50, sleep_between=2.0, goal="explore and learn"):
    """
    Legacy interface - wraps the new AutonomousAgent.

    For new code, use AutonomousAgent directly or run:
        python -m src.autonomous_agent --goal "your goal"
    """
    config = AgentConfig(
        ticks_per_decision=max(1, int(sleep_between / 0.6)),  # Convert sleep to ticks
    )

    agent = AutonomousAgent(config, goal)
    agent.run(max_ticks=max_iterations * config.ticks_per_decision)


if __name__ == "__main__":
    main()
