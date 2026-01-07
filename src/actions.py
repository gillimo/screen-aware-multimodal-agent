from __future__ import annotations

from dataclasses import dataclass, field
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.humanization import get_active_profile

ALLOWED_ACTIONS = {"move", "click", "drag", "type", "scroll", "camera"}


@dataclass
class ActionIntent:
    intent_id: str
    action_type: str
    target: Dict[str, Any]
    confidence: float = 1.0
    required_cues: List[str] = field(default_factory=list)
    gating: Dict[str, Any] = field(default_factory=dict)
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult:
    intent_id: str
    success: bool
    failure_reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalPolicy:
    require_approval: bool = True
    unsafe_actions: List[str] = field(default_factory=lambda: ["drag", "type", "camera"])
    auto_approve_actions: List[str] = field(default_factory=list)


class ActionExecutor:
    def execute(self, intent: ActionIntent) -> ActionResult:
        raise NotImplementedError


class DryRunExecutor(ActionExecutor):
    def execute(self, intent: ActionIntent) -> ActionResult:
        return ActionResult(intent_id=intent.intent_id, success=True, details={"dry_run": True})


class ActionLogger:
    def __init__(self, path: Optional[Path] = None):
        if path is None:
            root = Path(__file__).resolve().parents[1]
            path = root / "logs" / "actions.jsonl"
        path.parent.mkdir(exist_ok=True)
        self.path = path

    def log(self, intent: ActionIntent, result: ActionResult) -> None:
        profile = get_active_profile()
        if profile and "humanization_profile" not in intent.payload:
            intent.payload["humanization_profile"] = profile
        record = {
            "intent": intent.__dict__,
            "result": result.__dict__,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")


def validate_action_intent(intent: ActionIntent) -> List[str]:
    errors: List[str] = []
    if intent.action_type not in ALLOWED_ACTIONS:
        errors.append(f"unsupported action_type: {intent.action_type}")
    if not isinstance(intent.target, dict) or not intent.target:
        errors.append("target must be a non-empty object")
    if not 0 <= intent.confidence <= 1:
        errors.append("confidence must be between 0 and 1")
    return errors


def default_backoff_ms(attempt: int, base_ms: int = 120, max_ms: int = 800) -> int:
    return min(max_ms, base_ms * attempt)


def pre_action_gate(intent: ActionIntent, snapshot: Optional[Dict[str, Any]] = None) -> List[str]:
    errors: List[str] = []
    if snapshot is None:
        return errors

    if "ui" not in snapshot or not isinstance(snapshot.get("ui"), dict):
        errors.append("snapshot missing ui")
    if "client" not in snapshot or not isinstance(snapshot.get("client"), dict):
        errors.append("snapshot missing client")

    client = snapshot.get("client", {})
    ui = snapshot.get("ui", {})
    cues = snapshot.get("cues", {})

    require_focus = intent.gating.get("require_focus", True)
    if require_focus and not client.get("focused", False):
        errors.append("client not focused")

    require_hover = intent.gating.get("require_hover_text")
    if require_hover:
        actual = ui.get("hover_text", "")
        if require_hover.lower() not in actual.lower():
            errors.append("hover_text mismatch")

    require_open = intent.gating.get("require_open_interface")
    if require_open:
        if ui.get("open_interface") != require_open:
            errors.append("open_interface mismatch")

    for cue in intent.required_cues:
        val = cues.get(cue)
        if not val or str(val).lower() in {"none", "unknown"}:
            errors.append(f"missing cue {cue}")
    return errors


def post_action_verify(
    intent: ActionIntent,
    snapshot_after: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    if snapshot_after is None:
        return False, "no_post_snapshot"

    ui = snapshot_after.get("ui", {})
    expect_open = intent.gating.get("expect_open_interface")
    if expect_open and ui.get("open_interface") != expect_open:
        return False, "expected_interface_missing"

    expect_cursor = intent.gating.get("expect_cursor_state")
    if expect_cursor and ui.get("cursor_state") != expect_cursor:
        return False, "expected_cursor_state_missing"

    return True, ""


def should_abort_action(
    snapshot_before: Optional[Dict[str, Any]],
    snapshot_after: Optional[Dict[str, Any]],
) -> bool:
    if snapshot_before is None or snapshot_after is None:
        return False

    ui_before = snapshot_before.get("ui", {})
    ui_after = snapshot_after.get("ui", {})
    cues_before = snapshot_before.get("cues", {})
    cues_after = snapshot_after.get("cues", {})

    if ui_before.get("open_interface") != ui_after.get("open_interface"):
        return True
    if cues_before.get("modal_state") != cues_after.get("modal_state"):
        return True
    return False


def should_confirm_irreversible(action_label: str, chance: float = 0.7) -> bool:
    irreversible = {"drop", "alch", "trade"}
    if action_label not in irreversible:
        return False
    return random.random() < chance


def should_check_hover_text(chance: float = 0.6) -> bool:
    return random.random() < chance


def vary_action_order(actions: List[Any], variability_rate: float = 0.2) -> List[Any]:
    if variability_rate <= 0 or len(actions) < 2:
        return list(actions)
    if random.random() < variability_rate:
        shuffled = list(actions)
        random.shuffle(shuffled)
        return shuffled
    return list(actions)


def execute_with_retry(
    executor: ActionExecutor,
    intent: ActionIntent,
    verify_fn=None,
    max_attempts: int = 2,
    backoff_fn=None,
    sleep_fn=None,
) -> ActionResult:
    last_reason = ""
    for attempt in range(1, max_attempts + 1):
        result = executor.execute(intent)
        if verify_fn is None:
            result.details["attempts"] = attempt
            return result

        ok, reason = verify_fn(intent)
        if ok:
            return ActionResult(intent_id=intent.intent_id, success=True, details={"attempts": attempt})
        last_reason = reason

        if backoff_fn is not None and sleep_fn is not None:
            backoff_ms = backoff_fn(attempt)
            if backoff_ms:
                sleep_fn(backoff_ms / 1000.0)

    return ActionResult(
        intent_id=intent.intent_id,
        success=False,
        failure_reason=last_reason or "post_check_failed",
        details={"attempts": max_attempts},
    )


def execute_dry_run(intent: ActionIntent, logger: Optional[ActionLogger] = None) -> ActionResult:
    profile = get_active_profile()
    if profile:
        intent.payload["humanization_profile"] = profile
    executor = DryRunExecutor()
    result = executor.execute(intent)
    if logger is not None:
        logger.log(intent, result)
    return result


def requires_approval(intent: ActionIntent, policy: ApprovalPolicy) -> bool:
    if not policy.require_approval:
        return False
    if intent.action_type in policy.auto_approve_actions:
        return False
    return intent.action_type in policy.unsafe_actions


def focus_recovery_needed(snapshot: Optional[Dict[str, Any]]) -> bool:
    if not snapshot or "client" not in snapshot:
        return True
    return not snapshot.get("client", {}).get("focused", False)


def build_focus_recovery_intent(
    x: int,
    y: int,
    intent_id: str = "focus_recovery",
) -> ActionIntent:
    return ActionIntent(
        intent_id=intent_id,
        action_type="click",
        target={"x": x, "y": y},
        confidence=1.0,
        gating={"require_focus": False},
    )
