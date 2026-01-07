# Humanization Profiles

Purpose: define where human-like input presets live and how they are selected.

## Storage
- Default profiles: `data/humanization_profiles.json`
- Custom overrides: `data/humanization_profiles.local.json` (optional)

## Profile Fields
- timing: reaction (optionally per action), hover dwell, click dwell, pressure, settle jitter, inter-action delays.
- motion: curvature, acceleration, overshoot, micro-jitter, camera drag path alternates, micro-adjustment nudges.
- errors: misclick and correction rates.
- session: burst/rest, fatigue drift, optional cooldown, and optional per-session seed.
- idle: idle rates, scan/pause timing, edge/offscreen travel, and tab toggle keys.
- scroll: tick count and pause timing for scroll bursts.
- typing: per-key delays, burst sizing, corrections/backspace, and overlap timing.
- input_noise: frame-time variance adjustments layered onto step delays.
- attention: micro drift and bias offsets applied to targets.
- gates: default safety gates (e.g., require focus) applied during execution.
- hover gating: optionally enforce hover text match before click when expected hover is provided.
- interrupts: enable pause behavior on unexpected UI/modals during execution.
- device: DPI and polling jitter.

## Selection
- CLI flag or UI setting chooses the active profile.
- Profiles are versioned for reproducibility.
- CLI: `python run_app.py profile-select --profile normal`
