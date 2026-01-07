# Data Retention Policy

Purpose: define how long to keep traces, screenshots, and logs.

## Data Types
- Action traces and input events.
- Screen captures and annotated screenshots.
- Snapshot JSON and derived cues.
- Calibration datasets.

## Retention Guidelines
- Keep raw traces and screenshots for a limited window (default 30 days).
- Keep aggregated metrics and summaries long-term.
- Allow manual purge for any session.

## Storage Rules
- Store data locally by default.
- Use separate folders for raw and derived data.
- Avoid storing credentials or sensitive account details.
