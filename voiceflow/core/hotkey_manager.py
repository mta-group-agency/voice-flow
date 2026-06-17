"""
Global hotkey listener using pynput. Supports single keys and combinations.
Combo string format: comma-separated pynput key strings, e.g. "Key.ctrl,Key.cmd"
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from pynput import keyboard

_NORMALIZE = {
    "Key.ctrl_l": "Key.ctrl",
    "Key.ctrl_r": "Key.ctrl",
    "Key.shift_l": "Key.shift",
    "Key.shift_r": "Key.shift",
    "Key.alt_l": "Key.alt",
}


def _key_to_str(key) -> str:
    if isinstance(key, keyboard.Key):
        s = f"Key.{key.name}"
        return _NORMALIZE.get(s, s)
    if isinstance(key, keyboard.KeyCode) and key.char:
        return f"'{key.char}'"
    return ""


class HotkeyManager(QObject):
    hotkey_pressed = pyqtSignal()
    hotkey_released = pyqtSignal()
    cancel_pressed = pyqtSignal()

    def __init__(self, hotkey_str: str = "Key.alt_r"):
        super().__init__()
        self._hotkey_str = hotkey_str
        self._target: set[str] = self._parse(hotkey_str)
        self._held: set[str] = set()
        self._active = False
        self._suppressed = False
        self._listener: Optional[keyboard.Listener] = None

    def _parse(self, combo_str: str) -> set[str]:
        parts = {p.strip() for p in combo_str.split(",") if p.strip()}
        return parts if parts else {"Key.alt_r"}

    def reconfigure(self, hotkey_str: str):
        self._hotkey_str = hotkey_str
        self._target = self._parse(hotkey_str)
        self._held.clear()
        self._active = False

    def set_suppressed(self, suppressed: bool):
        self._suppressed = suppressed

    def start(self):
        if self._listener and self._listener.is_alive():
            return
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None

    def _on_press(self, key):
        if key == keyboard.Key.esc:
            self.cancel_pressed.emit()
            return
        if self._suppressed:
            return
        s = _key_to_str(key)
        if not s:
            return
        self._held.add(s)
        if not self._active and self._target.issubset(self._held):
            self._active = True
            self.hotkey_pressed.emit()

    def _on_release(self, key):
        s = _key_to_str(key)
        self._held.discard(s)  # always track, even when suppressed
        if self._suppressed:
            return
        if self._active and s in self._target:
            self._active = False
            self.hotkey_released.emit()
