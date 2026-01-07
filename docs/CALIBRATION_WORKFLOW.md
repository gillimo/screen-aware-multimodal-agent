# Calibration Workflow

Purpose: define how to fit human-like timing and motion parameters to baselines.

## Inputs
- Human trace datasets (mouse paths, click timing, camera drags).
- Snapshot cues (animation boundaries, hover text) for context alignment.

## Steps
1) Collect baseline traces for a defined task set.
2) Normalize traces by resolution, DPI, and framerate.
3) Fit distributions for timing and motion features.
4) Validate against acceptance thresholds.
5) Store profile parameters with version tags.

## Outputs
- InputProfile presets (subtle, normal, heavy).
- Calibration report with summary stats.
- Updated human-likeness metrics baselines.
