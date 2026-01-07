import sys
import time
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple


if sys.platform != "win32":
    raise RuntimeError("input_exec is only supported on Windows.")


PUL = ctypes.POINTER(ctypes.c_ulong)


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]


class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]

    _anonymous_ = ("_input",)
    _fields_ = [("type", wintypes.DWORD), ("_input", _INPUT)]


INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


def _send_input(*inputs):
    n_inputs = len(inputs)
    array_type = INPUT * n_inputs
    input_array = array_type(*inputs)
    ctypes.windll.user32.SendInput(n_inputs, ctypes.byref(input_array), ctypes.sizeof(INPUT))


def _screen_size() -> Tuple[int, int]:
    width = ctypes.windll.user32.GetSystemMetrics(0)
    height = ctypes.windll.user32.GetSystemMetrics(1)
    return width, height


def get_cursor_pos() -> Tuple[int, int]:
    point = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
    return int(point.x), int(point.y)


def move_mouse(x: int, y: int) -> None:
    width, height = _screen_size()
    abs_x = int(x * 65535 / max(1, width - 1))
    abs_y = int(y * 65535 / max(1, height - 1))
    inp = INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(abs_x, abs_y, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None))
    _send_input(inp)


def move_mouse_path(
    x: int,
    y: int,
    steps: int = 20,
    curve_strength: float = 0.15,
    jitter_px: float = 0.0,
    step_delay_ms: float = 0.0,
    start_jitter_px: float = 0.0,
    edge_margin_px: float = 4.0,
    speed_ramp_mode: str = "ease_in_out",
) -> None:
    from src.mouse_pathing import generate_path, add_tremor, generate_speed_ramp
    from src.mouse_pathing import jitter_start_point

    start = get_cursor_pos()
    if start_jitter_px:
        start = jitter_start_point(start, radius_px=float(start_jitter_px))
    path = generate_path(start, (x, y), steps=steps, curve_strength=curve_strength, easing="ease_in_out")
    if jitter_px:
        path = add_tremor(path, amplitude_px=jitter_px)
    width, height = _screen_size()
    margin = max(0.0, float(edge_margin_px))
    max_x = max(0.0, width - 1 - margin)
    max_y = max(0.0, height - 1 - margin)
    ramp = generate_speed_ramp(len(path), mode=speed_ramp_mode)
    for idx, (px, py) in enumerate(path):
        clamped_x = max(margin, min(max_x, px))
        clamped_y = max(margin, min(max_y, py))
        move_mouse(int(clamped_x), int(clamped_y))
        if step_delay_ms:
            factor = 0.4 + 1.2 * ramp[idx]
            time.sleep(float(step_delay_ms) * factor / 1000.0)


def click(button: str = "left", dwell_ms: Optional[float] = None, pressure_ms: Optional[float] = None) -> None:
    if button == "right":
        down = MOUSEEVENTF_RIGHTDOWN
        up = MOUSEEVENTF_RIGHTUP
    else:
        down = MOUSEEVENTF_LEFTDOWN
        up = MOUSEEVENTF_LEFTUP
    _send_input(INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, down, 0, None)))
    if pressure_ms:
        time.sleep(float(pressure_ms) / 1000.0)
    if dwell_ms:
        time.sleep(float(dwell_ms) / 1000.0)
    _send_input(INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, up, 0, None)))


def scroll(amount: int) -> None:
    delta = 120 * amount
    _send_input(INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, delta, MOUSEEVENTF_WHEEL, 0, None)))


def type_text(text: str, delay_ms: Optional[int] = None) -> None:
    for ch in text:
        scan = ord(ch)
        _send_input(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(0, scan, KEYEVENTF_UNICODE, 0, None)))
        _send_input(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(0, scan, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None)))
        if delay_ms:
            time.sleep(delay_ms / 1000.0)


def press_key(vk_code: int, hold_ms: Optional[float] = None) -> None:
    _send_input(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(vk_code, 0, 0, 0, None)))
    if hold_ms:
        time.sleep(float(hold_ms) / 1000.0)
    _send_input(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(vk_code, 0, KEYEVENTF_KEYUP, 0, None)))


def press_key_name(name: str, hold_ms: Optional[float] = None) -> None:
    key = name.strip().upper()
    if key.startswith("F") and key[1:].isdigit():
        idx = int(key[1:])
        if 1 <= idx <= 24:
            press_key(0x70 + (idx - 1), hold_ms=hold_ms)
            return
    if key == "ESC" or key == "ESCAPE":
        press_key(0x1B, hold_ms=hold_ms)
        return
    if len(key) == 1:
        press_key(ord(key), hold_ms=hold_ms)


def drag(start: Tuple[int, int], end: Tuple[int, int], hold_ms: Optional[int] = None) -> None:
    move_mouse(start[0], start[1])
    _send_input(INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, None)))
    if hold_ms:
        time.sleep(hold_ms / 1000.0)
    move_mouse(end[0], end[1])
    _send_input(INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, None)))
