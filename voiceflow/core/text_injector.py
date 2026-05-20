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

    def __init__(self, hotkey_manager=None):
        self._keyboard = Controller()
        self._hotkey_manager = hotkey_manager

    def inject(self, text: str):
        if not text.strip():
            return

        clipboard: QClipboard = QApplication.clipboard()
        previous = clipboard.text()

        if self._hotkey_manager:
            self._hotkey_manager.set_suppressed(True)

        # setText is synchronous on Windows — no sleep needed
        clipboard.setText(text)

        self._keyboard.press(Key.ctrl)
        self._keyboard.press("v")
        self._keyboard.release("v")
        self._keyboard.release(Key.ctrl)

        def restore():
            clipboard.setText(previous)
            if self._hotkey_manager:
                self._hotkey_manager.set_suppressed(False)

        QTimer.singleShot(self.RESTORE_DELAY_MS, restore)
