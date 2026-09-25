import ctypes
import os
import sys
import winreg
from ctypes import Structure, byref, c_int
from pathlib import Path

DATA_DIR_DISPLAY = "%APPDATA%\\VoiceFlow"
PASTE_DELAY_S = 0

_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "VoiceFlow"


def data_dir() -> Path:
    return Path(os.environ.get("APPDATA", Path.home())) / "VoiceFlow"


def ensure_single_instance():
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, "VoiceFlow_SingleInstance_Mutex")
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        ctypes.windll.user32.MessageBoxW(
            0,
            "VoiceFlow is already running.\nCheck the system tray.",
            "VoiceFlow",
            0x40,  # MB_ICONINFORMATION
        )
        sys.exit(0)
    return mutex


def autostart_is_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, _APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def autostart_enable(exe: str) -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, f'"{exe}"')
        winreg.CloseKey(key)
        return True
    except OSError:
        return False


def autostart_disable() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, _APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return True  # already absent
    except OSError:
        return False


def open_folder(path) -> None:
    os.startfile(str(path))


def paste_modifier():
    from pynput.keyboard import Key
    return Key.ctrl


class _MARGINS(Structure):
    _fields_ = [
        ("cxLeftWidth", c_int), ("cxRightWidth", c_int),
        ("cyTopHeight", c_int), ("cyBottomHeight", c_int),
    ]


def apply_window_shadow(win_id: int) -> None:
    try:
        ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(win_id, byref(_MARGINS(1, 1, 1, 1)))
    except Exception:
        pass


def show_startup_permission_hint() -> None:
    pass
