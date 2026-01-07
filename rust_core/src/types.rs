//! Common types for detection results

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DetectionResult {
    pub arrow: Option<Point>,
    pub highlight: Option<Point>,
    pub capture_ms: u64,
    pub detect_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Point {
    pub x: i32,
    pub y: i32,
    pub confidence: f32,
}

impl DetectionResult {
    pub fn empty() -> Self {
        Self {
            arrow: None,
            highlight: None,
            capture_ms: 0,
            detect_ms: 0,
        }
    }
}
