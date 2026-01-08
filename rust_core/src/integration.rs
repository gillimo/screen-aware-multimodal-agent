//! Fast integration layer for the canonical JSON action-intent pipeline.
//!
//! Handles data transformation and validation at native speed:
//! - Snapshot schema normalization
//! - Intent validation
//! - RSProx data parsing
//! - Pipeline timing enforcement

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::Instant;

/// Timing budgets in milliseconds
pub const RSPROX_POLL_MS: u64 = 50;
pub const PERCEPTION_MS: u64 = 100;
pub const DECISION_MS: u64 = 200;
pub const EXECUTION_MS: u64 = 150;
pub const VERIFICATION_MS: u64 = 50;
pub const TOTAL_BUDGET_MS: u64 = 600;

// =============================================================================
// SNAPSHOT SCHEMA TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SnapshotSchema {
    pub capture_id: String,
    pub timestamp: String,
    pub version: u32,
    pub stale: bool,
    pub session_id: String,
    pub client: ClientInfo,
    pub roi: RoiInfo,
    pub ui: UiInfo,
    pub ocr: Vec<OcrEntry>,
    pub cues: CuesInfo,
    pub derived: DerivedInfo,
    pub account: AccountInfo,
    pub runelite_data: RuneliteData,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ClientInfo {
    pub window_title: String,
    pub bounds: Bounds,
    pub focused: bool,
    pub scale: f32,
    pub fps: u32,
    pub capture_latency_ms: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Bounds {
    pub x: i32,
    pub y: i32,
    pub width: i32,
    pub height: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct RoiInfo {
    pub minimap: Bounds,
    pub inventory: Bounds,
    pub chatbox: Bounds,
    pub game_view: Bounds,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct UiInfo {
    pub open_interface: String,
    pub selected_tab: String,
    pub cursor_state: String,
    pub hover_text: String,
    pub elements: Vec<UiElement>,
    pub dialogue_options: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct UiElement {
    pub id: String,
    pub element_type: String,
    pub bounds: Bounds,
    pub visible: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct OcrEntry {
    pub region: String,
    pub text: String,
    pub confidence: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct CuesInfo {
    pub animation_state: String,
    pub highlight_state: String,
    pub modal_state: String,
    pub hover_text: String,
    pub chat_prompt: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct DerivedInfo {
    pub location: LocationInfo,
    pub activity: ActivityInfo,
    pub combat: CombatInfo,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct LocationInfo {
    pub region: String,
    pub subarea: String,
    pub coordinates: WorldCoord,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct WorldCoord {
    pub x: i32,
    pub y: i32,
    pub plane: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ActivityInfo {
    pub activity_type: String,
    pub state: String,
    pub progress: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct CombatInfo {
    pub state: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AccountInfo {
    pub name: String,
    pub membership_status: String,
    pub skills: HashMap<String, SkillInfo>,
    pub inventory: Vec<InventoryItem>,
    pub equipment: HashMap<String, String>,
    pub resources: ResourceInfo,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SkillInfo {
    pub level: u32,
    pub xp: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct InventoryItem {
    pub slot: u32,
    pub item_id: i32,
    pub name: String,
    pub quantity: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ResourceInfo {
    pub gp: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct RuneliteData {
    pub fresh: bool,
    pub tutorial_progress: i32,
    pub inventory_count: i32,
    pub camera_direction: String,
    pub npcs_on_screen: Vec<NpcInfo>,
    pub player_screen: Option<(i32, i32)>,
    pub player_world: Option<(i32, i32, i32)>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct NpcInfo {
    pub name: String,
    pub id: i32,
    pub x: i32,
    pub y: i32,
}

// =============================================================================
// ACTION INTENT TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActionIntent {
    pub intent_id: String,
    pub action_type: String,
    pub target: ActionTarget,
    pub confidence: f32,
    pub required_cues: Vec<String>,
    pub gating: GatingConfig,
    pub payload: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ActionTarget {
    pub x: Option<i32>,
    pub y: Option<i32>,
    pub name: Option<String>,
    pub ui_element: Option<String>,
    pub npc_id: Option<i32>,
    pub object_id: Option<i32>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct GatingConfig {
    pub require_hover: bool,
    pub require_visible: bool,
    pub timeout_ms: u32,
}

// =============================================================================
// VALIDATION
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationResult {
    pub valid: bool,
    pub errors: Vec<String>,
    pub validation_ms: u64,
}

const VALID_ACTION_TYPES: &[&str] = &[
    "click", "move", "drag", "key", "scroll", "wait",
    "walk", "interact", "dialogue", "inventory", "camera",
];

/// Validate an action intent at native speed
pub fn validate_intent(intent: &ActionIntent) -> ValidationResult {
    let start = Instant::now();
    let mut errors = Vec::new();

    // Check action type
    if intent.action_type.is_empty() {
        errors.push("Missing required field: action_type".to_string());
    } else if !VALID_ACTION_TYPES.contains(&intent.action_type.as_str()) {
        errors.push(format!("Invalid action_type: {}", intent.action_type));
    }

    // Check target for actions that require it
    let requires_target = ["click", "interact", "walk", "drag"];
    if requires_target.contains(&intent.action_type.as_str()) {
        let has_target = intent.target.x.is_some()
            || intent.target.name.is_some()
            || intent.target.ui_element.is_some()
            || intent.target.npc_id.is_some()
            || intent.target.object_id.is_some();

        if !has_target {
            errors.push(format!(
                "Action type '{}' requires target",
                intent.action_type
            ));
        }
    }

    // Check confidence range
    if intent.confidence < 0.0 || intent.confidence > 1.0 {
        errors.push(format!("Confidence out of range: {}", intent.confidence));
    }

    ValidationResult {
        valid: errors.is_empty(),
        errors,
        validation_ms: start.elapsed().as_millis() as u64,
    }
}

/// Validate a snapshot against the schema
pub fn validate_snapshot(snapshot: &SnapshotSchema) -> ValidationResult {
    let start = Instant::now();
    let mut errors = Vec::new();

    // Check required top-level fields
    if snapshot.capture_id.is_empty() {
        errors.push("Missing capture_id".to_string());
    }
    if snapshot.timestamp.is_empty() {
        errors.push("Missing timestamp".to_string());
    }
    if snapshot.session_id.is_empty() {
        errors.push("Missing session_id".to_string());
    }

    // Check client bounds
    if snapshot.client.bounds.width <= 0 || snapshot.client.bounds.height <= 0 {
        errors.push("Invalid client bounds".to_string());
    }

    ValidationResult {
        valid: errors.is_empty(),
        errors,
        validation_ms: start.elapsed().as_millis() as u64,
    }
}

// =============================================================================
// REGION INFERENCE (FAST)
// =============================================================================

/// Fast region inference from world coordinates
pub fn infer_region(x: i32, y: i32) -> &'static str {
    // Tutorial Island
    if x >= 3050 && x <= 3150 && y >= 3050 && y <= 3150 {
        return "Tutorial Island";
    }
    // Lumbridge
    if x >= 3200 && x <= 3250 && y >= 3200 && y <= 3250 {
        return "Lumbridge";
    }
    // Varrock
    if x >= 3180 && x <= 3290 && y >= 3380 && y <= 3500 {
        return "Varrock";
    }
    // Falador
    if x >= 2940 && x <= 3040 && y >= 3310 && y <= 3400 {
        return "Falador";
    }
    // Draynor
    if x >= 3080 && x <= 3120 && y >= 3230 && y <= 3280 {
        return "Draynor";
    }
    // Al Kharid
    if x >= 3270 && x <= 3330 && y >= 3140 && y <= 3200 {
        return "Al Kharid";
    }
    // Edgeville
    if x >= 3080 && x <= 3110 && y >= 3480 && y <= 3520 {
        return "Edgeville";
    }
    // Barbarian Village
    if x >= 3070 && x <= 3110 && y >= 3410 && y <= 3440 {
        return "Barbarian Village";
    }

    "unknown"
}

/// Infer tutorial phase from varbit value
pub fn infer_tutorial_phase(varbit_281: i32) -> &'static str {
    match varbit_281 {
        0 => "character_creation",
        1..=9 => "gielinor_guide",
        10..=19 => "gielinor_guide",
        20..=69 => "survival_expert",
        70..=119 => "master_chef",
        120..=169 => "quest_guide",
        170..=229 => "mining_instructor",
        230..=269 => "combat_instructor",
        270..=309 => "financial_advisor",
        310..=399 => "brother_brace",
        400..=499 => "magic_instructor",
        500..=599 => "magic_instructor_final",
        600.. => "completed",
        _ => "unknown",
    }
}

// =============================================================================
// PIPELINE TIMING
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineMetrics {
    pub stage_name: String,
    pub latency_ms: u64,
    pub budget_ms: u64,
    pub over_budget: bool,
}

/// Check if a stage is over budget
pub fn check_stage_timing(stage: &str, latency_ms: u64) -> PipelineMetrics {
    let budget = match stage {
        "rsprox_poll" => RSPROX_POLL_MS,
        "perception" => PERCEPTION_MS,
        "decision" => DECISION_MS,
        "execution" => EXECUTION_MS,
        "verification" => VERIFICATION_MS,
        _ => TOTAL_BUDGET_MS,
    };

    PipelineMetrics {
        stage_name: stage.to_string(),
        latency_ms,
        budget_ms: budget,
        over_budget: latency_ms > budget,
    }
}

// =============================================================================
// NORMALIZATION
// =============================================================================

/// Normalize raw RuneLite JSON to snapshot schema (fast path)
pub fn normalize_runelite_data(raw_json: &str) -> Result<RuneliteData, String> {
    serde_json::from_str(raw_json).map_err(|e| e.to_string())
}

/// Fast snapshot merge - combine detection results with RuneLite data
pub fn merge_snapshot_data(
    runelite: &RuneliteData,
    arrow: Option<(i32, i32, f32)>,
    highlight: Option<(i32, i32, f32)>,
    capture_ms: u64,
) -> SnapshotSchema {
    let mut snapshot = SnapshotSchema::default();

    // Copy RuneLite data
    snapshot.runelite_data = runelite.clone();
    snapshot.stale = !runelite.fresh;

    // Set location from player world coords
    if let Some((x, y, plane)) = runelite.player_world {
        snapshot.derived.location.coordinates = WorldCoord { x, y, plane };
        snapshot.derived.location.region = infer_region(x, y).to_string();
    }

    // Add detection results to cues
    if arrow.is_some() {
        snapshot.cues.highlight_state = "arrow".to_string();
    } else if highlight.is_some() {
        snapshot.cues.highlight_state = "object".to_string();
    }

    // Set capture latency
    snapshot.client.capture_latency_ms = capture_ms as u32;

    snapshot
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_intent_valid() {
        let intent = ActionIntent {
            intent_id: "test_1".to_string(),
            action_type: "click".to_string(),
            target: ActionTarget {
                x: Some(100),
                y: Some(200),
                ..Default::default()
            },
            confidence: 0.9,
            required_cues: vec![],
            gating: GatingConfig::default(),
            payload: HashMap::new(),
        };

        let result = validate_intent(&intent);
        assert!(result.valid);
        assert!(result.errors.is_empty());
    }

    #[test]
    fn test_validate_intent_missing_target() {
        let intent = ActionIntent {
            intent_id: "test_2".to_string(),
            action_type: "click".to_string(),
            target: ActionTarget::default(),
            confidence: 0.9,
            required_cues: vec![],
            gating: GatingConfig::default(),
            payload: HashMap::new(),
        };

        let result = validate_intent(&intent);
        assert!(!result.valid);
        assert!(result.errors.iter().any(|e| e.contains("requires target")));
    }

    #[test]
    fn test_infer_region() {
        assert_eq!(infer_region(3100, 3100), "Tutorial Island");
        assert_eq!(infer_region(3222, 3218), "Lumbridge");
        assert_eq!(infer_region(3200, 3400), "Varrock");
        assert_eq!(infer_region(0, 0), "unknown");
    }

    #[test]
    fn test_infer_tutorial_phase() {
        assert_eq!(infer_tutorial_phase(0), "character_creation");
        assert_eq!(infer_tutorial_phase(10), "gielinor_guide");
        assert_eq!(infer_tutorial_phase(50), "survival_expert");
        assert_eq!(infer_tutorial_phase(700), "completed");
    }
}
