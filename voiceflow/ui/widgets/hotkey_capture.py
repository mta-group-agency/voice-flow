"""
Widget that captures a key combination using pynput listener.
Supports Win key and multi-key combos like Ctrl+Win.
"""
from __future__ import annotations

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import QPushButton
from pynput import keyboard

_NORMALIZE = {
    "Key.ctrl_l": "Key.ctrl",
    "Key.ctrl_r": "Key.ctrl",
    "Key.shift_l": "Key.shift",
    "Key.shift_r": "Key.shift",
    "Key.alt_l": "Key.alt",
}

_DISPLAY = {
    "Key.ctrl": "Ctrl",
    "Key.shift": "Shift",
    "Key.alt": "Alt",
    "Key.alt_r": "AltGr",
    "Key.cmd": "Win",
    "Key.cmd_r": "Win R",
    "Key.caps_lock": "Caps Lock",
    "Key.tab": "Tab",
    "Key.esc": "Escape",
    "Key.enter": "Enter",
    "Key.space": "Space",
    **{f"Key.f{i}": f"F{i}" for i in range(1, 13)},
}

_MODIFIER_ORDER = [
    "Key.ctrl", "Key.shift", "Key.alt", "Key.alt_r", "Key.cmd", "Key.cmd_r"
]


def _key_to_str(key) -> str:
    if isinstance(key, keyboard.Key):
        s = f"Key.{key.name}"
        return _NORMALIZE.get(s, s)
    if isinstance(key, keyboard.KeyCode) and key.char:
        return f"'{key.char}'"
    return ""


def combo_display(combo_str: str) -> str:
    parts = [p.strip() for p in combo_str.split(",") if p.strip()]
    return " + ".join(_DISPLAY.get(p, p) for p in parts)


class HotkeyCaptureWidget(QPushButton):
    key_captured = pyqtSignal(str)

    def __init__(self, current_key: str = "Key.alt_r", parent=None):
        super().__init__(parent)
        self._key = current_key
        self._capturing = False
        self._held: set[str] = set()
        self._listener = None
        self._update_label()
        self.clicked.connect(self._start_capture)
        self.setFixedWidth(200)

    def _update_label(self):
        self.setText(combo_display(self._key))

    def _start_capture(self):
        if self._capturing:
            return
        self._capturing = True
        self._held.clear()
        self.setText("Press keys… (release to confirm)")
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def _on_press(self, key):
        s = _key_to_str(key)
        if s:
            self._held.add(s)

    def _on_release(self, key):
        if not self._capturing or not self._held:
            return
        self._capturing = False
        if self._listener:
            self._listener.stop()
            self._listener = None
        modifiers = [k for k in _MODIFIER_ORDER if k in self._held]
        others = sorted(k for k in self._held if k not in _MODIFIER_ORDER)
        ordered = modifiers + others
        if ordered:
            self._key = ",".join(ordered)
        QTimer.singleShot(0, self._finalize)

    def _finalize(self):
        self._update_label()
        self.key_captured.emit(self._key)

    def current_key(self) -> str:
        return self._key

    def set_key(self, key: str):
        self._key = key
        self._update_label()
