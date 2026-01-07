# OCR + UI Region Maps

Purpose: define placeholder region maps for OCR/UI detector configuration. Replace zeros with real bounds.

- OCR regions: `data/ocr_regions.json`
- UI detector regions: `data/ui_detector_regions.json`
- ROI presets: `data/roi.json`
- OCR config: `data/ocr_config.json`

Notes:
- Bounds are `x`, `y`, `width`, `height` relative to the game window.
- Use fixed, resizable, or fullscreen presets to match the client mode.
