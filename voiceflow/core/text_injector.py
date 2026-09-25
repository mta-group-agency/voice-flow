"""
Injects text into the currently active window via clipboard + Ctrl+V (Cmd+V on macOS).
Saves and restores the previous clipboard content.
"""

import time

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QClipboard
from PyQt6.QtWidgets import QApplication
from pynput.keyboard import Controller

from voiceflow.platform import PASTE_DELAY_S, paste_modifier, restore_target_app


class TextInjector:
    RESTORE_DELAY_MS = 1000

    def __init__(self, hotkey_manager=None, hotkey_managers=None):
        self._keyboard = Controller()
        self._paste_modifier = paste_modifier()
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

        # setText is synchronous on Windows (PASTE_DELAY_S is 0 there); macOS needs a moment
        clipboard.setText(text)
        if PASTE_DELAY_S:
            time.sleep(PASTE_DELAY_S)
        restore_target_app()

        self._keyboard.press(self._paste_modifier)
        self._keyboard.press("v")
        self._keyboard.release("v")
        self._keyboard.release(self._paste_modifier)

        def restore():
            clipboard.setText(previous)
            for m in self._hotkey_managers:
                m.set_suppressed(False)

        QTimer.singleShot(self.RESTORE_DELAY_MS, restore)
