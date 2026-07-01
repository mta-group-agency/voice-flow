"""
Injects text into the currently active window via clipboard + Ctrl+V.
Saves and restores the previous clipboard content.
"""

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QClipboard
from PyQt6.QtWidgets import QApplication
from pynput.keyboard import Controller, Key


class TextInjector:
    RESTORE_DELAY_MS = 1000

    def __init__(self, hotkey_manager=None, hotkey_managers=None):
        self._keyboard = Controller()
        managers = list(hotkey_managers) if hotkey_managers else []
        if hotkey_manager is not None:
            managers.append(hotkey_manager)
        self._hotkey_managers = managers

    def inject(self, text: str):
        if not text.strip():
            return

        clipboard: QClipboard = QApplication.clipboard()
        previous = clipboard.text()

        for m in self._hotkey_managers:
            m.set_suppressed(True)

        # setText is synchronous on Windows — no sleep needed
        clipboard.setText(text)

        self._keyboard.press(Key.ctrl)
        self._keyboard.press("v")
        self._keyboard.release("v")
        self._keyboard.release(Key.ctrl)

        def restore():
            clipboard.setText(previous)
            for m in self._hotkey_managers:
                m.set_suppressed(False)

        QTimer.singleShot(self.RESTORE_DELAY_MS, restore)
