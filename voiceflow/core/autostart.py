"""
Start at login: HKCU Run key on Windows, a LaunchAgent on macOS (see voiceflow.platform).
Works only when running as the compiled app (sys.frozen).
"""

import sys

from voiceflow.platform import autostart_disable, autostart_enable, autostart_is_enabled


def _exe_path() -> str | None:
    if getattr(sys, "frozen", False):
        return sys.executable
    return None


def is_enabled() -> bool:
    return autostart_is_enabled()


def enable() -> bool:
    exe = _exe_path()
    if not exe:
        return False
    return autostart_enable(exe)


def disable() -> bool:
    return autostart_disable()


def set_enabled(enabled: bool) -> bool:
    return enable() if enabled else disable()


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)
