# Human Mimicry Rubric

Purpose: a concrete, repeatable rubric to score mimicry and model behavior against human baselines.

Scoring:
- Each dimension is scored 0-5, then weighted.
- Total score = sum(weight * (score / 5.0)) * 100.
- Evidence is required for any score above 3.

## Rubric Dimensions (Weighted)

1) Timing realism (weight 0.20)
   - 0: fixed timing or identical per action.
   - 3: clear variance with occasional pauses and reaction delays.
   - 5: distribution matches human baselines (p50/p90 within 10%).
   Evidence: action_context timing stats + baseline capture.

2) Motion realism (weight 0.18)
   - 0: linear paths, no corrections.
   - 3: curved paths with jitter/overshoot.
   - 5: path curvature, speed ramps, and corrections match human traces.
   Evidence: path trace comparisons or feature stats.

3) Error model (weight 0.10)
   - 0: no mistakes or retries.
   - 3: misclick/correction rates present and bounded.
   - 5: error rates align with human baseline distribution.
   Evidence: action logs + error rate report.

4) Perception gating (weight 0.12)
   - 0: clicks without UI checks.
   - 3: hover/focus/occlusion checks present.
   - 5: gating accuracy mirrors human caution in low confidence.
   Evidence: skipped actions + hover checks.

5) Session rhythm (weight 0.10)
   - 0: uniform cadence.
   - 3: bursts/rest and fatigue drift.
   - 5: long-session pacing matches human cadence.
   Evidence: session pacing plots.

6) Camera + viewport behavior (weight 0.08)
   - 0: no camera motion.
   - 3: nudges/zoom pauses/alt drags.
   - 5: camera actions mirror human corrections and pauses.
   Evidence: action_context camera timing.

7) Typing realism (weight 0.07)
   - 0: constant per-key delay.
   - 3: bursts and occasional corrections.
   - 5: cadence/overlap/typo rates align to baseline.
   Evidence: typing timing logs.

8) Decision quality (model) (weight 0.10)
   - 0: invalid JSON or frequent schema errors.
   - 3: valid decisions with occasional suboptimal steps.
   - 5: stable, context-aware decisions with high success rate.
   Evidence: decision trace success metrics.

9) Chat + social behavior (model) (weight 0.05)
   - 0: no responses or unsafe responses.
   - 3: rate-limited, context-safe responses.
   - 5: human-like timing and phrasing with safe guardrails.
   Evidence: chat logs with cooldown metrics.

## Scoring Worksheet (Fill Per Run)

Run ID:
Model version:
Profile:
Scenario:

Timing realism: score __ /5, evidence:
Motion realism: score __ /5, evidence:
Error model: score __ /5, evidence:
Perception gating: score __ /5, evidence:
Session rhythm: score __ /5, evidence:
Camera + viewport: score __ /5, evidence:
Typing realism: score __ /5, evidence:
Decision quality: score __ /5, evidence:
Chat + social behavior: score __ /5, evidence:

Total score: __ /100

Notes:
Dependencies:

