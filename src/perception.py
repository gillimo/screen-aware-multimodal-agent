from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes


@dataclass(frozen=True)
class WindowInfo:
    handle: int
    title: str
    bounds: Tuple[int, int, int, int]
    focused: bool


def _get_window_bounds(handle: int) -> Tuple[int, int, int, int]:
    rect = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(handle, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def _get_window_title(handle: int) -> str:
    length = ctypes.windll.user32.GetWindowTextLengthW(handle)
    buffer = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(handle, buffer, length + 1)
    return buffer.value


def is_window_focused(handle: int) -> bool:
    if sys.platform != "win32":
        return False
    foreground = ctypes.windll.user32.GetForegroundWindow()
    return int(foreground) == int(handle)




def focus_window(handle: int, wait_ms: int = 100) -> bool:
    """Bring window to foreground and wait for it to gain focus."""
    if sys.platform != "win32":
        return False
    try:
        ctypes.windll.user32.SetForegroundWindow(handle)
        if wait_ms > 0:
            time.sleep(wait_ms / 1000.0)
        return is_window_focused(handle)
    except Exception:
        return False

def find_windows(title_contains: str) -> List[WindowInfo]:
    if sys.platform != "win32":
        return []

    matches: List[WindowInfo] = []
    foreground = ctypes.windll.user32.GetForegroundWindow()

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def enum_proc(handle, _param):
        if not ctypes.windll.user32.IsWindowVisible(handle):
            return True
        title = _get_window_title(handle)
        if title_contains.lower() in title.lower():
            bounds = _get_window_bounds(handle)
            focused = handle == foreground
            matches.append(WindowInfo(handle=int(handle), title=title, bounds=bounds, focused=focused))
        return True

    ctypes.windll.user32.EnumWindows(enum_proc, 0)
    return matches


def find_window(title_contains: str) -> Optional[WindowInfo]:
    matches = find_windows(title_contains)
    return matches[0] if matches else None


def capture_frame(bounds: Tuple[int, int, int, int]) -> Dict[str, Any]:
    left, top, right, bottom = bounds
    width = max(0, right - left)
    height = max(0, bottom - top)
    if width == 0 or height == 0:
        raise ValueError("bounds must be non-zero")

    start = time.perf_counter()
    image = _capture_image(bounds)
    latency_ms = int((time.perf_counter() - start) * 1000)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "bounds": {"x": left, "y": top, "width": width, "height": height},
        "image": image,
        "capture_latency_ms": latency_ms,
    }


def capture_session(
    bounds: Tuple[int, int, int, int],
    fps: float,
    duration_s: float,
    window_handle: Optional[int] = None,
) -> Dict[str, Any]:
    if fps <= 0:
        raise ValueError("fps must be > 0")
    if duration_s <= 0:
        raise ValueError("duration_s must be > 0")

    interval = 1.0 / fps
    start_time = time.perf_counter()
    frames: List[Dict[str, Any]] = []
    dropped = 0
    latency_values: List[int] = []
    focus_samples: List[bool] = []

    while True:
        now = time.perf_counter()
        if now - start_time >= duration_s:
            break

        frame = capture_frame(bounds)
        latency_values.append(frame["capture_latency_ms"])
        if window_handle is not None:
            focus_samples.append(is_window_focused(window_handle))
        frames.append(
            {
                "timestamp": frame["timestamp"],
                "capture_latency_ms": frame["capture_latency_ms"],
            }
        )
        if frame["capture_latency_ms"] > int(interval * 1000):
            dropped += 1

        elapsed = time.perf_counter() - now
        sleep_for = interval - elapsed
        if sleep_for > 0:
            time.sleep(sleep_for)

    if latency_values:
        avg_latency = sum(latency_values) / len(latency_values)
        max_latency = max(latency_values)
    else:
        avg_latency = 0
        max_latency = 0

    if focus_samples:
        focused_count = sum(1 for focused in focus_samples if focused)
    else:
        focused_count = 0

    return {
        "fps_target": fps,
        "duration_s": duration_s,
        "frames_captured": len(frames),
        "dropped_frames": dropped,
        "avg_capture_latency_ms": round(avg_latency, 2),
        "max_capture_latency_ms": max_latency,
        "focused_frames": focused_count,
        "focus_samples": focus_samples,
        "frames": frames,
    }


def _capture_image(bounds: Tuple[int, int, int, int]):
    left, top, right, bottom = bounds
    try:
        import mss
    except Exception:
        mss = None

    if mss is not None:
        with mss.mss() as sct:
            return sct.grab({"left": left, "top": top, "width": right - left, "height": bottom - top})

    try:
        from PIL import ImageGrab
    except Exception as exc:
        raise RuntimeError("No capture backend available. Install mss or Pillow.") from exc

    return ImageGrab.grab(bbox=(left, top, right, bottom))


def save_frame(bounds: Tuple[int, int, int, int], path: str) -> bool:
    image = _capture_image(bounds)
    try:
        if hasattr(image, "save"):
            image.save(path)
            return True
        if hasattr(image, "rgb") and hasattr(image, "size"):
            try:
                from PIL import Image
            except Exception:
                return False
            raw = Image.frombytes("RGB", image.size, image.rgb)
            raw.save(path)
            return True
    except Exception:
        return False
    return False
