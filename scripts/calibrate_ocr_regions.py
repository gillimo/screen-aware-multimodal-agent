from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.perception import find_window


def build_regions(bounds, margin_x: int = 8, margin_top: int = 30, margin_bottom: int = 8):
    x, y, width, height = bounds
    inner_x = x + margin_x
    inner_y = y + margin_top
    inner_width = max(1, width - (margin_x * 2))
    inner_height = max(1, height - margin_top - margin_bottom)
    regions = {
        "chat_box": {
            "x": inner_x + int(inner_width * 0.02),
            "y": inner_y + int(inner_height * 0.68),
            "width": int(inner_width * 0.42),
            "height": int(inner_height * 0.28),
        },
        "hover_text": {
            "x": inner_x + int(inner_width * 0.02),
            "y": inner_y + int(inner_height * 0.02),
            "width": int(inner_width * 0.50),
            "height": int(inner_height * 0.08),
        },
        "dialogue": {
            "x": inner_x + int(inner_width * 0.18),
            "y": inner_y + int(inner_height * 0.58),
            "width": int(inner_width * 0.64),
            "height": int(inner_height * 0.24),
        },
        "inventory": {
            "x": inner_x + int(inner_width * 0.72),
            "y": inner_y + int(inner_height * 0.44),
            "width": int(inner_width * 0.26),
            "height": int(inner_height * 0.52),
        },
        "tooltips": {
            "x": inner_x + int(inner_width * 0.55),
            "y": inner_y + int(inner_height * 0.05),
            "width": int(inner_width * 0.40),
            "height": int(inner_height * 0.18),
        },
    }
    roi = {
        "chat_box": regions["chat_box"],
        "minimap": {
            "x": inner_x + int(inner_width * 0.80),
            "y": inner_y + int(inner_height * 0.05),
            "width": int(inner_width * 0.18),
            "height": int(inner_height * 0.24),
        },
        "inventory": regions["inventory"],
    }
    return regions, roi


def main():
    parser = argparse.ArgumentParser(description="Generate OCR/ROI regions from current window bounds.")
    parser.add_argument("--title", default="Old School RuneScape")
    parser.add_argument("--out", default="data/ocr_regions.json")
    parser.add_argument("--roi-out", default="data/roi.json")
    parser.add_argument("--margin-x", type=int, default=8)
    parser.add_argument("--margin-top", type=int, default=30)
    parser.add_argument("--margin-bottom", type=int, default=8)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    window = find_window(args.title)
    if not window:
        raise SystemExit(f"No window found matching: {args.title}")

    bounds = (
        window.bounds[0],
        window.bounds[1],
        window.bounds[2] - window.bounds[0],
        window.bounds[3] - window.bounds[1],
    )
    regions, roi = build_regions(
        bounds,
        margin_x=args.margin_x,
        margin_top=args.margin_top,
        margin_bottom=args.margin_bottom,
    )
    (root / args.out).write_text(json.dumps(regions, indent=2), encoding="utf-8")
    roi_payload = {"fullscreen": roi, "fixed": roi, "resizable": roi, "version": 1}
    (root / args.roi_out).write_text(json.dumps(roi_payload, indent=2), encoding="utf-8")
    print(f"Wrote OCR regions to {args.out}")
    print(f"Wrote ROI presets to {args.roi_out}")


if __name__ == "__main__":
    main()
