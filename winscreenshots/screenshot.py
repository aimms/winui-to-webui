from pyaimms_bridge import aimms_model
import ctypes
import ctypes.wintypes
from PIL import ImageGrab


def make_screenshot(fn: str) -> None:
    """
    Screenshot of the primary monitor to file fn (PNG).
    AIMMS must be running on the primary monitor.
    """
    user32 = ctypes.windll.user32

    found_hwnd = ctypes.wintypes.HWND(0)
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

    def _find(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if 'AIMMS' in buf.value:
            found_hwnd.value = hwnd
            return False
        return True

    user32.EnumWindows(EnumWindowsProc(_find), 0)

    if not found_hwnd.value:
        raise RuntimeError("No AIMMS window found on screen")

    ImageGrab.grab().save(fn)
