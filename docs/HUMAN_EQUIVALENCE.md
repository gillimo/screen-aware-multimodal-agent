# Human Equivalence Requirements (AgentOSRS)

Purpose: define measurable criteria, datasets, and tooling to validate human-equivalent eyes and hands.

## Definition
Human-equivalent means the agent's perception and input traces are statistically indistinguishable from a human baseline for the same tasks, within a defined confidence threshold and task scope.

## Scope
- Applies to F2P workflows and the OSRS original client overlay.
- Requires paired human sessions to establish baselines.
- Requires auditability and reproducibility of evaluation runs.

## Acceptance Criteria (Pass/Fail)
- Perception parity: snapshot fields match human-annotated ground truth within tolerance (OCR accuracy, UI element detection, state classification).
- Timing parity: reaction, dwell, inter-action, and pause distributions align with baseline within set bounds.
- Motion parity: cursor path curvature, speed profiles, overshoot, and micro-jitter align with baseline.
- Error parity: misclick, correction, and recovery rates align with baseline.
- Session rhythm parity: bursts, rest periods, and fatigue drift match baseline.
- End-to-end behavior parity: task completion time and action sequences fall within baseline variance.

### Concrete Thresholds (Initial)
Perception
- OCR accuracy: >= 98% character accuracy on chat/tooltips; >= 95% on small UI labels.
- UI element detection: >= 99% precision and >= 95% recall for core panels/tabs.
- State classification accuracy: >= 95% for activity state and combat state.

Timing
- Reaction time distribution: mean within ±10% of baseline, KS test p-value >= 0.05.
- Dwell time (pre-click): mean within ±15% of baseline, stdev within ±20%.
- Inter-action delays: mean within ±15% of baseline, 95th percentile within ±20%.

Motion
- Path curvature (mean absolute curvature): within ±20% of baseline.
- Velocity profile: peak speed within ±15%, accel/decel slope within ±20%.
- Overshoot rate: within ±25% of baseline.
- Micro-jitter: mean amplitude within ±20% of baseline.

Errors and Recovery
- Misclick rate: within ±25% of baseline.
- Correction rate: within ±25% of baseline.
- Recovery time after error: within ±20% of baseline.

Session Rhythm
- Burst length (actions per burst): mean within ±20% of baseline.
- Rest duration: mean within ±20% of baseline.
- Fatigue drift rate: within ±25% of baseline.

End-to-End
- Task completion time: within ±15% of baseline.
- Action sequence similarity: >= 0.85 normalized edit similarity to baseline traces.

Notes
- Thresholds are per-task and must be tuned after dataset collection.
- Failing any mandatory category is a fail for human-equivalence.

## Datasets
- Human input trace dataset (mouse, key, camera) with timestamps.
- Human session video with aligned UI annotations.
- OCR ground-truth labels for chat, tooltips, and interfaces.
- Task-specific baselines (skilling loop, banking loop, quest dialogue).

### Dataset Manifest Template (human_baseline_manifest.json)
```json
{
  "dataset_id": "baseline_f2p_v1",
  "created_at": "YYYY-MM-DDTHH:MM:SSZ",
  "source": {
    "collector": "handle",
    "machine_id": "string",
    "os_version": "string",
    "client_build": "string",
    "display": { "resolution": "1920x1080", "refresh_hz": 60 }
  },
  "tasks": [
    {
      "task_id": "skilling_woodcutting_lumbridge",
      "description": "Chop and bank logs in Lumbridge",
      "session_ids": [ "sess_001", "sess_002" ],
      "annotations": {
        "ui_labels": "path/to/ui_labels.jsonl",
        "ocr_labels": "path/to/ocr_labels.jsonl"
      }
    }
  ],
  "files": {
    "input_traces": [ "path/to/input_trace_001.jsonl" ],
    "video": [ "path/to/video_001.mp4" ],
    "snapshots": [ "path/to/snapshots_001.jsonl" ]
  }
}
```

## Tooling
- Capture + annotate pipeline for human sessions.
- Replay-to-comparison harness (agent vs. human).
- Statistical comparison suite with configurable thresholds.
- Calibration tooling to fit distributions to baselines.
- Human-equivalence report generator (pass/fail with deltas).

## Reporting
- Store per-run metrics with schema version and dataset ID.
- Track regression trends over time.
