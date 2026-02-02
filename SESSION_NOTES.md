# Session Notes - Terminal Restart Required

## What Was Installed (via winget)
1. **Rust** (rustup) - for fast perception module
2. **Java JDK 11** (Eclipse Temurin) - for RuneLite plugin

**RESTART TERMINAL** for PATH to update!

---

## After Terminal Restart - Build Steps

### 1. Build Rust Core Module
```bash
cd C:\Users\gilli\OneDrive\Desktop\projects\agentosrs\rust_core
cargo build --release
# Then copy the DLL:
copy target\release\osrs_core.dll ..\osrs_core.pyd
```

### 2. Build RuneLite Plugin
```bash
cd C:\Users\gilli\OneDrive\Desktop\projects\agentosrs\runelite_plugin
gradlew.bat build
# JAR will be in build\libs\
```

### 3. Install Plugin in RuneLite
- Open RuneLite
- Go to Configuration (wrench icon)
- Find "Plugin" section → click folder icon
- Copy JAR from `runelite_plugin\build\libs\` to that folder
- Restart RuneLite

---

## Architecture Summary

```
┌──────────────────────────────────────────────────┐
│              OSRS Agent Stack                    │
├──────────────────────────────────────────────────┤
│  fast_perception.py  ← Main entry point          │
│       ├── RuneLite Data (NPCs, player, camera)   │
│       │      └── ~/.runelite/session_stats.json  │
│       └── Pixel Detection (arrow, highlight)     │
│              ├── Rust: osrs_core.pyd (FAST)      │
│              └── Python fallback (slower)        │
├──────────────────────────────────────────────────┤
│  "Session Stats" RuneLite Plugin                 │
│       └── Exports game data every 2 ticks        │
├──────────────────────────────────────────────────┤
│  Rust Core (rust_core/)                          │
│       ├── Screen capture (screenshots crate)     │
│       ├── Yellow arrow detection                 │
│       ├── Cyan highlight detection               │
│       └── PyO3 bindings → osrs_core.pyd          │
├──────────────────────────────────────────────────┤
│  Decision Layer                                  │
│       ├── Local: phi3 via Ollama (text only)     │
│       └── Claude: Vision when stuck (escalation) │
├──────────────────────────────────────────────────┤
│  Action Layer                                    │
│       └── Human-like mouse/keyboard (src/actions)│
└──────────────────────────────────────────────────┘
```

---

## Key Files Created/Modified

### Rust Core (`rust_core/`)
- `Cargo.toml` - Dependencies (pyo3, screenshots, rayon, serde)
- `src/lib.rs` - PyO3 module definition
- `src/capture.rs` - Screen capture functions
- `src/detection.rs` - Arrow/highlight pixel detection
- `src/types.rs` - DetectionResult structs

### RuneLite Plugin (`runelite_plugin/`)
- `src/main/java/com/sessionstats/SessionStatsPlugin.java` - Main plugin
- `src/main/java/com/sessionstats/SessionStatsConfig.java` - Config
- Exports to: `~/.runelite/session_stats.json`

### Python (`src/`)
- `fast_perception.py` - Unified perception (Rust + RuneLite + fallback)
- `runelite_data.py` - Read/parse RuneLite export data
- `target_finder.py` - Smart target finding (walk only when needed)
- `librarian_server.py` - Updated for config-based model selection

### Build Scripts (`scripts/`)
- `build_rust.bat` - Build Rust and copy to project
- `build_plugin.bat` - Build RuneLite plugin

---

## API Key Setup (for Claude escalation)

Set environment variable:
```
set ANTHROPIC_API_KEY=YOUR_KEY_HERE
```

Or the librarian server reads from `data/claude_config.json`:
```json
{
  "api_key_env": "ANTHROPIC_API_KEY",
  "vision_model": "claude-sonnet-4-20250514",
  "text_model": "claude-3-5-haiku-20241022"
}
```

---

## Current Tutorial Island Status

- Player is at the pond area (near fishing spots)
- Need to find and talk to Survival Expert
- Tutorial progress varbit: check via RuneLite export

---

## Next Steps After Restart

1. Build Rust module
2. Build RuneLite plugin
3. Load plugin into RuneLite
4. Test `fast_perception.py` to verify data flow
5. Continue Tutorial Island automation

---

## Tickets Added (docs/TICKETS.md)

### Performance Optimization - Rust Core
- Target: process within 1 game tick (~600ms)
- Rust for perception, Python for decisions

### RuneLite API Integration
- Export player, NPCs, camera, inventory, skills
- Tutorial progress varbit

### Tutorial Island Completion
- Not covered by Quest Helper - handle ourselves
- Phase-based progression
