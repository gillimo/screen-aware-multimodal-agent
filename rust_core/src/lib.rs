//! OSRS Core - Fast perception and detection for the agent
//!
//! Handles performance-critical tasks:
//! - Screen capture
//! - Arrow/highlight detection
//! - ROI extraction

use pyo3::prelude::*;

mod capture;
mod detection;
mod types;

use capture::ScreenCapture;
use detection::{find_yellow_arrow, find_cyan_highlight};
use types::DetectionResult;

/// Capture a region of the screen
#[pyfunction]
fn capture_region(x: i32, y: i32, width: u32, height: u32) -> PyResult<Vec<u8>> {
    capture::capture_region(x, y, width, height)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
}

/// Find yellow Quest Helper arrow in image data
#[pyfunction]
fn detect_arrow(img_data: Vec<u8>, width: u32, height: u32) -> PyResult<Option<(i32, i32, f32)>> {
    Ok(find_yellow_arrow(&img_data, width, height))
}

/// Find cyan highlight in image data
#[pyfunction]
fn detect_highlight(img_data: Vec<u8>, width: u32, height: u32) -> PyResult<Option<(i32, i32, f32)>> {
    Ok(find_cyan_highlight(&img_data, width, height))
}

/// Capture and detect in one call (fastest)
#[pyfunction]
fn capture_and_detect(x: i32, y: i32, width: u32, height: u32) -> PyResult<String> {
    let result = capture::capture_and_analyze(x, y, width, height)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    Ok(serde_json::to_string(&result).unwrap_or_default())
}

/// Python module definition
#[pymodule]
fn osrs_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(capture_region, m)?)?;
    m.add_function(wrap_pyfunction!(detect_arrow, m)?)?;
    m.add_function(wrap_pyfunction!(detect_highlight, m)?)?;
    m.add_function(wrap_pyfunction!(capture_and_detect, m)?)?;
    Ok(())
}
