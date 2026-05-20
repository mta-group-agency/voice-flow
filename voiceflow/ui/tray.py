"""
System tray icon with context menu.
"""

from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from voiceflow.core.pipeline import State

_ASSETS = Path(__file__).parent.parent.parent / "assets"


def _icon(name: str) -> QIcon:
    path = _ASSETS / name
    if path.exists():
        return QIcon(str(path))
    return QIcon()


class TrayManager:
    def __init__(self, app, main_window, pipeline):
        self._tray = QSystemTrayIcon(app)
        self._pipeline = pipeline
        self._main_window = main_window
        self._last_text = ""

        self._icon_idle = _icon("icon.png")
        self._icon_rec = _icon("icon_rec.png")
        self._icon_proc = _icon("icon_proc.png")

        self._tray.setIcon(self._icon_idle)
        self._tray.setToolTip("VoiceFlow — idle")

        menu = QMenu()
        self._header_action = menu.addAction("VoiceFlow")
        self._header_action.setEnabled(False)
        menu.addSeparator()
        open_action = menu.addAction("Open VoiceFlow")
        open_action.triggered.connect(self._show_window)
        menu.addSeparator()
        self._last_action = menu.addAction("No transcription yet")
        self._last_action.setEnabled(False)
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(app.quit)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)

        pipeline.state_changed.connect(self._on_state_changed)
        pipeline.transcription_ready.connect(self._on_transcription_ready)

        self._tray.show()

    def _show_window(self):
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _on_state_changed(self, state):
        if state == State.IDLE:
            self._tray.setIcon(self._icon_idle)
            self._tray.setToolTip("VoiceFlow — idle")
        elif state == State.RECORDING:
            self._tray.setIcon(self._icon_rec)
            self._tray.setToolTip("VoiceFlow — recording…")
        else:
            self._tray.setIcon(self._icon_proc)
            self._tray.setToolTip("VoiceFlow — processing…")

    def _on_transcription_ready(self, text: str):
        self._last_text = text
        preview = text[:50] + ("…" if len(text) > 50 else "")
        self._last_action.setText(f'"{preview}"')

    def notify(self, title: str, message: str):
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)

    def notify_error(self, message: str):
        self._tray.showMessage("VoiceFlow", message, QSystemTrayIcon.MessageIcon.Warning, 4000)
