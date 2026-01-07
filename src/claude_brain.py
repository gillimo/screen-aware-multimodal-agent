"""Claude API integration for complex decision making."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def get_client() -> Optional[Any]:
    """Get Anthropic client if available."""
    if not HAS_ANTHROPIC:
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # Try loading from config
        config_path = DATA_DIR / "claude_config.json"
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text())
                api_key = config.get("api_key")
            except Exception:
                pass
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


def analyze_screenshot(
    screenshot_base64: str,
    tutorial_hint: str,
    hover_text: str,
    current_phase: str,
    question: str = "What should I click on to progress?",
) -> Optional[Dict[str, Any]]:
    """
    Use Claude to analyze screenshot and decide next action.

    Returns dict with:
        - action: 'click', 'wait', 'scan'
        - target: {x, y} approximate click location
        - reasoning: explanation
        - confidence: 0-1
    """
    client = get_client()
    if not client:
        return None

    prompt = f"""You are helping navigate OSRS Tutorial Island.

Current tutorial hint: "{tutorial_hint}"
Current hover text: "{hover_text}"
Current phase: {current_phase}

{question}

Look at the screenshot and identify:
1. Where is the flashing yellow arrow pointing (if visible)?
2. What should be clicked to progress the tutorial?
3. Approximate x,y coordinates (image is ~1140x710 pixels)

Respond in JSON format:
{{
    "action": "click" or "wait" or "scan",
    "target": {{"x": number, "y": number}},
    "target_description": "what you're clicking on",
    "reasoning": "why this action",
    "confidence": 0.0-1.0
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": screenshot_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )

        text = response.content[0].text
        # Extract JSON from response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception as e:
        print(f"Claude API error: {e}")
        return None

    return None


def should_use_claude(context: Dict[str, Any]) -> bool:
    """
    Decide if we should use Claude for this decision.

    Use Claude when:
    - Can't find expected target
    - Multiple retries failed
    - Complex navigation needed
    - Phase transition
    """
    repeat_count = context.get("repeat_count", 0)
    last_success = context.get("last_success", True)
    phase_changed = context.get("phase_changed", False)

    # Use Claude if stuck or at transition
    if repeat_count >= 2 and not last_success:
        return True
    if phase_changed:
        return True

    return False


def hybrid_decide(
    snapshot: Dict[str, Any],
    state: Dict[str, Any],
    local_decision: Optional[Dict[str, Any]],
    screenshot_b64: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Hybrid decision: try local first, escalate to librarian if stuck.
    """
    from src.librarian_client import ask_librarian

    context = {
        "repeat_count": state.get("repeat_count", 0),
        "last_success": state.get("last_execution", {}).get("success_count", 0) > 0,
        "phase_changed": False,
    }

    # If local decision exists and we're not stuck, use it
    if local_decision and not should_use_claude(context):
        return {
            "source": "local",
            "decision": local_decision,
        }

    # Escalate to librarian (Claude-backed)
    tutorial_hint = ""
    hover_text = ""
    for ocr in snapshot.get("ocr", []):
        if ocr.get("region") == "tutorial_hint":
            tutorial_hint = ocr.get("text", "")[:100]
        if ocr.get("region") == "hover_text":
            hover_text = ocr.get("text", "")[:50]

    librarian_context = {
        "phase": state.get("phase", "unknown"),
        "tutorial_hint": tutorial_hint,
        "hover_text": hover_text,
        "repeat_count": context["repeat_count"],
    }

    answer = ask_librarian(
        question="What should I click to progress in the tutorial?",
        screenshot_b64=screenshot_b64,
        context=librarian_context,
    )

    if answer and answer.get("target"):
        return {
            "source": "librarian",
            "decision": {
                "decision_id": "librarian_assist",
                "intent": answer.get("target_description", "librarian suggestion"),
                "confidence": answer.get("confidence", 0.7),
                "rationale": [answer.get("reasoning", "")],
                "required_cues": [],
                "risks": [],
                "actions": [
                    {
                        "action_id": "librarian_click",
                        "action_type": "click",
                        "target": answer["target"],
                        "confidence": answer.get("confidence", 0.7),
                        "gating": {},
                        "payload": {},
                    }
                ],
            },
            "reasoning": answer.get("reasoning", ""),
        }

    # Fallback to local if librarian unavailable
    return {
        "source": "local_fallback",
        "decision": local_decision,
        "note": "Librarian unavailable",
    }
