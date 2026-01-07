from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import List, Optional

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes


RIM_TYPEMOUSE = 0
RIM_TYPEKEYBOARD = 1
RIM_TYPEHID = 2
RIDI_DEVICENAME = 0x20000007


@dataclass(frozen=True)
class InputDevice:
    device_id: str
    device_type: str
    name: str
    vendor_id: Optional[str] = None
    product_id: Optional[str] = None


def _parse_vid_pid(name: str) -> (Optional[str], Optional[str]):
    match = re.search(r"VID_([0-9A-Fa-f]{4}).*PID_([0-9A-Fa-f]{4})", name)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def enumerate_input_devices() -> List[InputDevice]:
    if sys.platform != "win32":
        return []

    class RAWINPUTDEVICELIST(ctypes.Structure):
        _fields_ = [("hDevice", wintypes.HANDLE), ("dwType", wintypes.DWORD)]

    count = wintypes.UINT(0)
    res = ctypes.windll.user32.GetRawInputDeviceList(None, ctypes.byref(count), ctypes.sizeof(RAWINPUTDEVICELIST))
    if res != 0:
        return []

    devices = (RAWINPUTDEVICELIST * count.value)()
    res = ctypes.windll.user32.GetRawInputDeviceList(devices, ctypes.byref(count), ctypes.sizeof(RAWINPUTDEVICELIST))
    if res == -1:
        return []

    results: List[InputDevice] = []
    for item in devices:
        name_size = wintypes.UINT(0)
        ctypes.windll.user32.GetRawInputDeviceInfoW(item.hDevice, RIDI_DEVICENAME, None, ctypes.byref(name_size))
        if name_size.value == 0:
            continue
        buffer = ctypes.create_unicode_buffer(name_size.value)
        ctypes.windll.user32.GetRawInputDeviceInfoW(
            item.hDevice, RIDI_DEVICENAME, buffer, ctypes.byref(name_size)
        )
        name = buffer.value
        if item.dwType == RIM_TYPEMOUSE:
            dev_type = "mouse"
        elif item.dwType == RIM_TYPEKEYBOARD:
            dev_type = "keyboard"
        else:
            dev_type = "hid"
        vid, pid = _parse_vid_pid(name)
        results.append(
            InputDevice(
                device_id=str(int(item.hDevice)),
                device_type=dev_type,
                name=name,
                vendor_id=vid,
                product_id=pid,
            )
        )
    return results


def get_display_refresh_rate() -> Optional[int]:
    if sys.platform != "win32":
        return None

    class DEVMODEW(ctypes.Structure):
        _fields_ = [
            ("dmDeviceName", wintypes.WCHAR * 32),
            ("dmSpecVersion", wintypes.WORD),
            ("dmDriverVersion", wintypes.WORD),
            ("dmSize", wintypes.WORD),
            ("dmDriverExtra", wintypes.WORD),
            ("dmFields", wintypes.DWORD),
            ("dmOrientation", wintypes.SHORT),
            ("dmPaperSize", wintypes.SHORT),
            ("dmPaperLength", wintypes.SHORT),
            ("dmPaperWidth", wintypes.SHORT),
            ("dmScale", wintypes.SHORT),
            ("dmCopies", wintypes.SHORT),
            ("dmDefaultSource", wintypes.SHORT),
            ("dmPrintQuality", wintypes.SHORT),
            ("dmColor", wintypes.SHORT),
            ("dmDuplex", wintypes.SHORT),
            ("dmYResolution", wintypes.SHORT),
            ("dmTTOption", wintypes.SHORT),
            ("dmCollate", wintypes.SHORT),
            ("dmFormName", wintypes.WCHAR * 32),
            ("dmLogPixels", wintypes.WORD),
            ("dmBitsPerPel", wintypes.DWORD),
            ("dmPelsWidth", wintypes.DWORD),
            ("dmPelsHeight", wintypes.DWORD),
            ("dmDisplayFlags", wintypes.DWORD),
            ("dmDisplayFrequency", wintypes.DWORD),
            ("dmICMMethod", wintypes.DWORD),
            ("dmICMIntent", wintypes.DWORD),
            ("dmMediaType", wintypes.DWORD),
            ("dmDitherType", wintypes.DWORD),
            ("dmReserved1", wintypes.DWORD),
            ("dmReserved2", wintypes.DWORD),
            ("dmPanningWidth", wintypes.DWORD),
            ("dmPanningHeight", wintypes.DWORD),
        ]

    ENUM_CURRENT_SETTINGS = -1
    devmode = DEVMODEW()
    devmode.dmSize = ctypes.sizeof(DEVMODEW)
    res = ctypes.windll.user32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(devmode))
    if res == 0:
        return None
    return int(devmode.dmDisplayFrequency)


def get_input_latency_ms() -> Optional[int]:
    return None
