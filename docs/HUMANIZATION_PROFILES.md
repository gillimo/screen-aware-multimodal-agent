# Humanization Profiles

Purpose: define where human-like input presets live and how they are selected.

## Storage
- Default profiles: `data/humanization_profiles.json`
- Custom overrides: `data/humanization_profiles.local.json` (optional)

## Profile Fields
- timing: reaction, click dwell, inter-action delays.
- motion: curvature, acceleration, overshoot, micro-jitter.
- errors: misclick and correction rates.
- session: burst/rest and fatigue drift.
- device: DPI and polling jitter.

## Selection
- CLI flag or UI setting chooses the active profile.
- Profiles are versioned for reproducibility.
- CLI: `python run_app.py profile-select --profile normal`
