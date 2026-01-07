# Human-Like Behavior Catalog

Purpose: enumerate the interaction behaviors (big and small) required to mimic a human operator.

## Perception and Response
- Reaction time variability to new stimuli (UI changes, chat, prompts).
- Brief re-checks before committing to high-impact actions.
- Slow down in visually complex or uncertain states.
- Quick confirmations when the state is stable and known.
- Momentary hesitation when new modals appear.
- Track subtle visual cues (animation start/end, hover text, highlight changes).
- Adapt responses to layout shifts, popups, or temporary overlays.

## Mouse Movement
- Curved paths with variable acceleration and deceleration.
- Cursor settle before clicking.
- Occasional overshoot and micro-corrections.
- Slight hand jitter in slow movements.
- Edge avoidance and non-linear paths to corners.
- Naturalized drag gestures (start hesitation, end jitter).

## Clicking
- Variable click timing and down/up dwell.
- Hover dwell before click.
- Target acquisition within a hitbox (not always center).
- Rare near-misses with safe recovery.
- Double-click timing variance where applicable.

## Keyboard Input
- Typing cadence with bursts and pauses.
- Minor corrections (backspace) and retry behavior.
- Modifier timing variance (shift/ctrl with clicks).

## Camera Movement
- Short camera nudges with slight over-rotation.
- Variable drag speed and direction choice.
- Occasional micro-adjustments after settling.
- Zoom adjustments with brief pauses.

## Session Rhythm
- Micro-pauses between actions.
- Bursts of activity followed by short rests.
- Longer breaks over extended sessions.
- Gradual pacing drift over time (fatigue model).

## Contextual Actions
- UI scan patterns before acting.
- Idle behaviors: hover, inventory check, panel toggles.
- Focus recovery when the client loses focus.
- Pause or abort on unexpected UI or chat interruptions.
- Use on-screen animation cadence to pace input.

## Safety and Verification
- Confirm UI state before irreversible actions.
- Retry with backoff after failed interactions.
- Abort actions if the target changes mid-action.

## Variability and Signature
- Per-session randomness with optional fixed seed for testing.
- Per-user profiles for timing, movement, and error rates.
- Avoid repeated identical action signatures.
