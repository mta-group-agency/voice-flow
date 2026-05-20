"""
Windows registry autostart via HKCU/Software/Microsoft/Windows/CurrentVersion/Run.
Works only when running as a compiled .exe (sys.frozen).
"""

import sys
import winreg

_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "VoiceFlow"


def _exe_path() -> str | None:
    if getattr(sys, "frozen", False):
        return sys.executable
    return None


def is_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, _APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable() -> bool:
    exe = _exe_path()
    if not exe:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, f'"{exe}"')
        winreg.CloseKey(key)
        return True
    except OSError:
        return False


def disable() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, _APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return True  # already absent
    except OSError:
        return False


def set_enabled(enabled: bool) -> bool:
    return enable() if enabled else disable()


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)
