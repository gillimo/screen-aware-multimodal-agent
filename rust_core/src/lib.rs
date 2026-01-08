//! OSRS Core - Fast perception and detection for the agent
//!
//! Handles performance-critical tasks:
//! - Screen capture
//! - Arrow/highlight detection
//! - ROI extraction
//! - Snapshot schema normalization (fast integration layer)
//! - Intent validation
//! - Pipeline timing enforcement

use pyo3::prelude::*;

mod capture;
mod detection;
mod integration;
mod types;

use capture::ScreenCapture;
use detection::{find_yellow_arrow, find_cyan_highlight};
use integration::{validate_intent, validate_snapshot, infer_region, infer_tutorial_phase, check_stage_timing};
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

// =============================================================================
// INTEGRATION LAYER FUNCTIONS
// =============================================================================

/// Fast intent validation
#[pyfunction]
fn validate_action_intent(intent_json: &str) -> PyResult<String> {
    let intent: integration::ActionIntent = serde_json::from_str(intent_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    let result = integration::validate_intent(&intent);
    Ok(serde_json::to_string(&result).unwrap_or_default())
}

/// Fast snapshot validation
#[pyfunction]
fn validate_snapshot_schema(snapshot_json: &str) -> PyResult<String> {
    let snapshot: integration::SnapshotSchema = serde_json::from_str(snapshot_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    let result = integration::validate_snapshot(&snapshot);
    Ok(serde_json::to_string(&result).unwrap_or_default())
}

/// Fast region inference from world coordinates
#[pyfunction]
fn get_region(x: i32, y: i32) -> String {
    integration::infer_region(x, y).to_string()
}

/// Fast tutorial phase inference
#[pyfunction]
fn get_tutorial_phase(varbit_281: i32) -> String {
    integration::infer_tutorial_phase(varbit_281).to_string()
}

/// Check pipeline stage timing
#[pyfunction]
fn check_timing(stage: &str, latency_ms: u64) -> PyResult<String> {
    let result = integration::check_stage_timing(stage, latency_ms);
    Ok(serde_json::to_string(&result).unwrap_or_default())
}

/// Get timing budgets
#[pyfunction]
fn get_timing_budgets() -> PyResult<String> {
    let budgets = serde_json::json!({
        "rsprox_poll_ms": integration::RSPROX_POLL_MS,
        "perception_ms": integration::PERCEPTION_MS,
        "decision_ms": integration::DECISION_MS,
        "execution_ms": integration::EXECUTION_MS,
        "verification_ms": integration::VERIFICATION_MS,
        "total_budget_ms": integration::TOTAL_BUDGET_MS,
    });
    Ok(serde_json::to_string(&budgets).unwrap_or_default())
}

/// Python module definition
#[pymodule]
fn osrs_core(_py: Python, m: &PyModule) -> PyResult<()> {
    // Detection functions
    m.add_function(wrap_pyfunction!(capture_region, m)?)?;
    m.add_function(wrap_pyfunction!(detect_arrow, m)?)?;
    m.add_function(wrap_pyfunction!(detect_highlight, m)?)?;
    m.add_function(wrap_pyfunction!(capture_and_detect, m)?)?;

    // Integration layer functions
    m.add_function(wrap_pyfunction!(validate_action_intent, m)?)?;
    m.add_function(wrap_pyfunction!(validate_snapshot_schema, m)?)?;
    m.add_function(wrap_pyfunction!(get_region, m)?)?;
    m.add_function(wrap_pyfunction!(get_tutorial_phase, m)?)?;
    m.add_function(wrap_pyfunction!(check_timing, m)?)?;
    m.add_function(wrap_pyfunction!(get_timing_budgets, m)?)?;

    Ok(())
}
