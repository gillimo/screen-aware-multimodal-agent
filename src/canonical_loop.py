"""
Canonical JSON Action-Intent Loop Integration.

This module implements the HIGH PRIORITY tickets for the canonical pipeline:
- Make JSON action-intent loop the default automation path
- Wire decision validation + trace logging into the loop
- Execute intents through policy/approval gating
- Align tutorial loop orchestration with canonical pipeline
- Define RSProx-first pipeline stages with timing budgets
- Gate heavy OCR behind stuck/uncertain triggers

Nightfall - 2026-01-07
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)


# =============================================================================
# TIMING BUDGETS (RSProx-first pipeline)
# =============================================================================

@dataclass
class TimingBudget:
    """Timing budget for pipeline stages."""
    rsprox_poll_ms: int = 50      # RSProx data poll (hot path)
    perception_ms: int = 100      # Fast perception (no OCR)
    decision_ms: int = 200        # Model decision
    execution_ms: int = 150       # Action execution
    verification_ms: int = 50     # Post-action check
    total_budget_ms: int = 600    # One game tick

    # Fallback path (when triggered)
    ocr_budget_ms: int = 500      # Heavy OCR allowance
    recovery_budget_ms: int = 1000  # Recovery actions


TIMING = TimingBudget()


# =============================================================================
# DECISION VALIDATION & TRACING
# =============================================================================

@dataclass
class DecisionTrace:
    """Trace record for a single decision."""
    decision_id: str
    timestamp: str
    session_id: str
    snapshot_id: str
    phase: str
    intent: Dict[str, Any]
    validation_errors: List[str]
    execution_result: Optional[Dict[str, Any]] = None
    latency_ms: int = 0
    fallback_triggered: bool = False
    fallback_reason: str = ""


class TraceLogger:
    """Logs decision traces to JSONL file."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.log_path = LOGS_DIR / f"trace_{session_id}.jsonl"
        self.traces: List[DecisionTrace] = []

    def log(self, trace: DecisionTrace) -> None:
        """Log a decision trace."""
        self.traces.append(trace)
        entry = {
            "decision_id": trace.decision_id,
            "timestamp": trace.timestamp,
            "session_id": trace.session_id,
            "snapshot_id": trace.snapshot_id,
            "phase": trace.phase,
            "intent": trace.intent,
            "validation_errors": trace.validation_errors,
            "execution_result": trace.execution_result,
            "latency_ms": trace.latency_ms,
            "fallback_triggered": trace.fallback_triggered,
            "fallback_reason": trace.fallback_reason,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def get_recent(self, n: int = 10) -> List[DecisionTrace]:
        """Get last N traces."""
        return self.traces[-n:]


def validate_intent(intent: Dict[str, Any]) -> List[str]:
    """
    Validate an action intent against the schema.

    Returns list of validation errors (empty if valid).
    """
    errors = []

    # Required fields
    if "action_type" not in intent:
        errors.append("Missing required field: action_type")

    action_type = intent.get("action_type", "")
    valid_types = [
        "click", "move", "drag", "key", "scroll", "wait",
        "walk", "interact", "dialogue", "inventory", "camera"
    ]
    if action_type and action_type not in valid_types:
        errors.append(f"Invalid action_type: {action_type}")

    # Target validation for click/interact
    if action_type in ("click", "interact", "walk"):
        target = intent.get("target", {})
        if not target:
            errors.append(f"Action type '{action_type}' requires target")
        elif not (target.get("x") or target.get("name") or target.get("ui_element")):
            errors.append("Target must have x/y, name, or ui_element")

    # Confidence range
    confidence = intent.get("confidence", 1.0)
    if not (0.0 <= confidence <= 1.0):
        errors.append(f"Confidence out of range: {confidence}")

    return errors


# =============================================================================
# POLICY & APPROVAL GATING
# =============================================================================

@dataclass
class PolicyConfig:
    """Policy configuration for action gating."""
    require_approval_for: List[str] = field(default_factory=lambda: [
        "trade", "drop_valuable", "logout", "bank_all"
    ])
    blocked_actions: List[str] = field(default_factory=list)
    rate_limits: Dict[str, int] = field(default_factory=lambda: {
        "trade": 1,  # Max 1 per minute
        "bank": 5,   # Max 5 per minute
    })
    dry_run: bool = False


class PolicyGate:
    """
    Gating layer that checks policy before execution.
    Integrates with human-in-the-loop approval when needed.
    """

    def __init__(self, config: PolicyConfig):
        self.config = config
        self.action_counts: Dict[str, List[float]] = {}
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}

    def check(self, intent: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if intent is allowed by policy.

        Returns:
            (allowed, reason)
        """
        action_type = intent.get("action_type", "")

        # Check blocked actions
        if action_type in self.config.blocked_actions:
            return False, f"Action '{action_type}' is blocked by policy"

        # Check rate limits
        if action_type in self.config.rate_limits:
            limit = self.config.rate_limits[action_type]
            now = time.time()
            # Clean old entries (older than 60s)
            counts = self.action_counts.get(action_type, [])
            counts = [t for t in counts if now - t < 60]
            self.action_counts[action_type] = counts

            if len(counts) >= limit:
                return False, f"Rate limit exceeded for '{action_type}' ({limit}/min)"

        # Check approval required
        if action_type in self.config.require_approval_for:
            intent_id = intent.get("intent_id", str(uuid.uuid4())[:8])
            if intent_id not in self.pending_approvals:
                self.pending_approvals[intent_id] = {
                    "intent": intent,
                    "requested_at": time.time(),
                    "approved": None,
                }
                return False, f"Awaiting approval for '{action_type}'"

            approval = self.pending_approvals[intent_id]
            if approval["approved"] is None:
                return False, f"Still awaiting approval for '{action_type}'"
            if not approval["approved"]:
                del self.pending_approvals[intent_id]
                return False, f"Action '{action_type}' was rejected"

            del self.pending_approvals[intent_id]

        return True, "allowed"

    def record_execution(self, action_type: str) -> None:
        """Record an action execution for rate limiting."""
        if action_type not in self.action_counts:
            self.action_counts[action_type] = []
        self.action_counts[action_type].append(time.time())

    def approve(self, intent_id: str) -> bool:
        """Approve a pending action."""
        if intent_id in self.pending_approvals:
            self.pending_approvals[intent_id]["approved"] = True
            return True
        return False

    def reject(self, intent_id: str) -> bool:
        """Reject a pending action."""
        if intent_id in self.pending_approvals:
            self.pending_approvals[intent_id]["approved"] = False
            return True
        return False


# =============================================================================
# CANONICAL LOOP STAGES
# =============================================================================

@dataclass
class PipelineStage:
    """Result from a pipeline stage."""
    name: str
    success: bool
    data: Any
    latency_ms: int
    error: Optional[str] = None


class CanonicalPipeline:
    """
    The canonical JSON action-intent pipeline.

    Stages:
    1. Perception (RSProx-first, fast path)
    2. Fallback check (trigger heavy OCR if needed)
    3. Decision (model inference)
    4. Validation (schema + policy check)
    5. Execution (with timing variance)
    6. Verification (post-action check)
    """

    def __init__(
        self,
        session_id: str,
        window_bounds: Tuple[int, int, int, int],
        policy_config: Optional[PolicyConfig] = None,
        decision_fn: Optional[Callable[[Dict], Dict]] = None,
        execute_fn: Optional[Callable[[Dict], bool]] = None,
    ):
        self.session_id = session_id
        self.window_bounds = window_bounds
        self.policy = PolicyGate(policy_config or PolicyConfig())
        self.tracer = TraceLogger(session_id)
        self.decision_fn = decision_fn
        self.execute_fn = execute_fn

        # Import integration modules
        self._import_modules()

        # State
        self.tick_count = 0
        self.stage_results: List[PipelineStage] = []

    def _import_modules(self) -> None:
        """Import integration modules (lazy to avoid circular imports)."""
        try:
            from src.snapshot_schema import (
                capture_snapshot_v2,
                get_fallback_trigger,
            )
            self.capture_snapshot = capture_snapshot_v2
            self.fallback_trigger = get_fallback_trigger()
        except ImportError as e:
            logger.warning(f"snapshot_schema not available: {e}")
            from src.fast_perception import capture_snapshot
            self.capture_snapshot = capture_snapshot
            self.fallback_trigger = None

        try:
            from src.tutorial_phases import TutorialOrchestrator, detect_phase
            self.tutorial_orchestrator = TutorialOrchestrator()
            self.detect_tutorial_phase = detect_phase
        except ImportError as e:
            logger.warning(f"tutorial_phases not available: {e}")
            self.tutorial_orchestrator = None
            self.detect_tutorial_phase = None

        try:
            from src.agent_tools import TimingVariance
            self.timing = TimingVariance()
        except ImportError as e:
            logger.warning(f"agent_tools not available: {e}")
            self.timing = None

    def run_stage(
        self,
        name: str,
        fn: Callable[[], Any],
        budget_ms: int,
    ) -> PipelineStage:
        """Run a pipeline stage with timing."""
        start = time.time()
        try:
            result = fn()
            latency = int((time.time() - start) * 1000)
            if latency > budget_ms:
                logger.warning(f"Stage '{name}' exceeded budget: {latency}ms > {budget_ms}ms")
            return PipelineStage(name=name, success=True, data=result, latency_ms=latency)
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            logger.error(f"Stage '{name}' failed: {e}")
            return PipelineStage(name=name, success=False, data=None, latency_ms=latency, error=str(e))

    def tick(self) -> Dict[str, Any]:
        """
        Execute one tick of the canonical pipeline.

        Returns dict with:
            - success: bool
            - decision_id: str
            - intent: dict (if any)
            - executed: bool
            - trace: DecisionTrace
        """
        self.tick_count += 1
        self.stage_results = []
        tick_start = time.time()

        decision_id = f"{self.session_id}_{self.tick_count}_{uuid.uuid4().hex[:6]}"

        # Stage 1: Perception (RSProx-first, fast path)
        perception_result = self.run_stage(
            "perception",
            lambda: self.capture_snapshot(
                window_bounds=self.window_bounds,
                session_id=self.session_id,
                force_ocr=False,
            ),
            TIMING.perception_ms,
        )
        self.stage_results.append(perception_result)

        if not perception_result.success:
            return self._make_result(decision_id, success=False, error="Perception failed")

        snapshot = perception_result.data

        # Stage 2: Fallback check
        fallback_triggered = False
        fallback_reason = "none"

        if self.fallback_trigger:
            fallback_triggered, fallback_reason = self.fallback_trigger.check(snapshot)
            if fallback_triggered:
                logger.info(f"Fallback triggered: {fallback_reason}")
                # Re-run with heavy OCR
                ocr_result = self.run_stage(
                    "ocr_fallback",
                    lambda: self.capture_snapshot(
                        window_bounds=self.window_bounds,
                        session_id=self.session_id,
                        force_ocr=True,
                    ),
                    TIMING.ocr_budget_ms,
                )
                self.stage_results.append(ocr_result)
                if ocr_result.success:
                    snapshot = ocr_result.data

        # Check tutorial phase
        phase = "unknown"
        if self.detect_tutorial_phase and snapshot.get("runelite_data"):
            rl_data = snapshot["runelite_data"]
            phase = self.detect_tutorial_phase(rl_data.get("tutorial_progress", 0), snapshot)
            snapshot["_tutorial_phase"] = phase.value if hasattr(phase, "value") else str(phase)

        # Stage 3: Decision
        intent = {}
        if self.decision_fn:
            decision_result = self.run_stage(
                "decision",
                lambda: self.decision_fn(snapshot),
                TIMING.decision_ms,
            )
            self.stage_results.append(decision_result)
            if decision_result.success and decision_result.data:
                intent = decision_result.data

        # Stage 4: Validation
        validation_errors = validate_intent(intent) if intent else []

        # Policy check
        policy_allowed = True
        policy_reason = "allowed"
        if intent and not validation_errors:
            policy_allowed, policy_reason = self.policy.check(intent)

        # Stage 5: Execution
        executed = False
        execution_result = None

        if intent and not validation_errors and policy_allowed:
            # Apply timing variance
            if self.timing:
                pre_delay = self.timing.pre_action_delay()
                time.sleep(pre_delay / 1000.0)

            if self.execute_fn:
                exec_stage = self.run_stage(
                    "execution",
                    lambda: self.execute_fn(intent),
                    TIMING.execution_ms,
                )
                self.stage_results.append(exec_stage)
                executed = exec_stage.success
                execution_result = {"success": executed, "error": exec_stage.error}

                if executed:
                    self.policy.record_execution(intent.get("action_type", ""))
                    if self.fallback_trigger:
                        self.fallback_trigger.record_success()
                else:
                    if self.fallback_trigger:
                        self.fallback_trigger.record_failure(exec_stage.error or "execution_failed")

                # Post-action timing variance
                if self.timing:
                    post_delay = self.timing.post_action_delay()
                    time.sleep(post_delay / 1000.0)

        # Create trace
        tick_latency = int((time.time() - tick_start) * 1000)
        trace = DecisionTrace(
            decision_id=decision_id,
            timestamp=datetime.now().isoformat(),
            session_id=self.session_id,
            snapshot_id=snapshot.get("capture_id", "unknown"),
            phase=phase if isinstance(phase, str) else (phase.value if hasattr(phase, "value") else "unknown"),
            intent=intent,
            validation_errors=validation_errors + ([policy_reason] if not policy_allowed else []),
            execution_result=execution_result,
            latency_ms=tick_latency,
            fallback_triggered=fallback_triggered,
            fallback_reason=fallback_reason,
        )
        self.tracer.log(trace)

        return self._make_result(
            decision_id,
            success=True,
            intent=intent,
            executed=executed,
            trace=trace,
            snapshot=snapshot,
        )

    def _make_result(
        self,
        decision_id: str,
        success: bool,
        error: Optional[str] = None,
        intent: Optional[Dict] = None,
        executed: bool = False,
        trace: Optional[DecisionTrace] = None,
        snapshot: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Build result dict."""
        return {
            "success": success,
            "decision_id": decision_id,
            "error": error,
            "intent": intent or {},
            "executed": executed,
            "trace": trace,
            "snapshot": snapshot,
            "stages": [
                {"name": s.name, "success": s.success, "latency_ms": s.latency_ms, "error": s.error}
                for s in self.stage_results
            ],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        traces = self.tracer.traces
        if not traces:
            return {"tick_count": self.tick_count, "traces": 0}

        latencies = [t.latency_ms for t in traces]
        fallbacks = sum(1 for t in traces if t.fallback_triggered)
        errors = sum(1 for t in traces if t.validation_errors)

        return {
            "tick_count": self.tick_count,
            "traces": len(traces),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "max_latency_ms": max(latencies),
            "fallback_rate": fallbacks / len(traces) if traces else 0,
            "error_rate": errors / len(traces) if traces else 0,
        }


# =============================================================================
# LOGGING BOUNDARIES
# =============================================================================

class LoggingConfig:
    """
    Logging boundaries for hot path vs fallback.

    Hot path (always-on): Minimal logging, metrics only
    Fallback path (on-demand): Full debug logging, screenshots
    """

    HOT_PATH_LEVEL = logging.WARNING  # Only warnings/errors on hot path
    FALLBACK_LEVEL = logging.DEBUG    # Full debug on fallback

    @classmethod
    def configure_hot_path(cls) -> None:
        """Configure logging for hot path (minimal)."""
        logging.getLogger("src.fast_perception").setLevel(cls.HOT_PATH_LEVEL)
        logging.getLogger("src.snapshot_schema").setLevel(cls.HOT_PATH_LEVEL)
        logging.getLogger("src.runelite_data").setLevel(cls.HOT_PATH_LEVEL)

    @classmethod
    def configure_fallback(cls) -> None:
        """Configure logging for fallback path (verbose)."""
        logging.getLogger("src.fast_perception").setLevel(cls.FALLBACK_LEVEL)
        logging.getLogger("src.snapshot_schema").setLevel(cls.FALLBACK_LEVEL)
        logging.getLogger("src.ocr").setLevel(cls.FALLBACK_LEVEL)


# =============================================================================
# TUTORIAL LOOP ALIGNMENT
# =============================================================================

class TutorialLoopAdapter:
    """
    Aligns tutorial loop orchestration with canonical pipeline.

    Maps tutorial phases to action intents.
    """

    def __init__(self, pipeline: CanonicalPipeline):
        self.pipeline = pipeline

    def get_tutorial_intent(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get action intent for current tutorial phase.

        Uses tutorial_phases.py orchestrator to determine next action.
        """
        if not self.pipeline.tutorial_orchestrator:
            return {}

        phase = snapshot.get("_tutorial_phase", "unknown")

        # Get actions from orchestrator
        try:
            actions = self.pipeline.tutorial_orchestrator.tick(snapshot)
            if actions:
                # Convert first action to intent format
                action = actions[0]
                return {
                    "action_type": action.get("type", "wait"),
                    "target": action.get("target", {}),
                    "confidence": action.get("confidence", 0.8),
                    "phase": phase,
                    "source": "tutorial_orchestrator",
                }
        except Exception as e:
            logger.warning(f"Tutorial orchestrator error: {e}")

        return {}


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "CanonicalPipeline",
    "PolicyConfig",
    "PolicyGate",
    "TimingBudget",
    "TIMING",
    "TraceLogger",
    "DecisionTrace",
    "validate_intent",
    "LoggingConfig",
    "TutorialLoopAdapter",
]
