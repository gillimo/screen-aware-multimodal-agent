//! Fast screen capture

use crate::detection::{find_cyan_highlight, find_yellow_arrow};
use crate::types::{DetectionResult, Point};
use std::time::Instant;

/// Capture a screen region and return raw RGB bytes
pub fn capture_region(x: i32, y: i32, width: u32, height: u32) -> Result<Vec<u8>, String> {
    #[cfg(target_os = "windows")]
    {
        use screenshots::Screen;

        let screens = Screen::all().map_err(|e| e.to_string())?;
        if screens.is_empty() {
            return Err("No screens found".to_string());
        }

        let screen = &screens[0];
        let image = screen
            .capture_area(x, y, width, height)
            .map_err(|e| e.to_string())?;

        Ok(image.into_raw())
    }

    #[cfg(not(target_os = "windows"))]
    {
        Err("Screen capture only supported on Windows".to_string())
    }
}

/// Capture and analyze in one optimized call
pub fn capture_and_analyze(x: i32, y: i32, width: u32, height: u32) -> Result<DetectionResult, String> {
    let capture_start = Instant::now();
    let img_data = capture_region(x, y, width, height)?;
    let capture_ms = capture_start.elapsed().as_millis() as u64;

    let detect_start = Instant::now();

    // Run detections in parallel using rayon
    let arrow = find_yellow_arrow(&img_data, width, height);
    let highlight = find_cyan_highlight(&img_data, width, height);

    let detect_ms = detect_start.elapsed().as_millis() as u64;

    Ok(DetectionResult {
        arrow: arrow.map(|(x, y, c)| Point { x, y, confidence: c }),
        highlight: highlight.map(|(x, y, c)| Point { x, y, confidence: c }),
        capture_ms,
        detect_ms,
    })
}

pub struct ScreenCapture {
    last_capture: Option<Vec<u8>>,
    width: u32,
    height: u32,
}

impl ScreenCapture {
    pub fn new() -> Self {
        Self {
            last_capture: None,
            width: 0,
            height: 0,
        }
    }

    pub fn capture(&mut self, x: i32, y: i32, width: u32, height: u32) -> Result<&[u8], String> {
        let data = capture_region(x, y, width, height)?;
        self.width = width;
        self.height = height;
        self.last_capture = Some(data);
        Ok(self.last_capture.as_ref().unwrap())
    }
}
