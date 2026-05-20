"""
VoiceFlow application bootstrap.
"""

from PyQt6.QtWidgets import QApplication

from voiceflow.config.settings_manager import SettingsManager
from voiceflow.core.pipeline import Pipeline, State
from voiceflow.storage.history_db import HistoryDB
from voiceflow.ui import theme as vf_theme
from voiceflow.ui.main_window import MainWindow
from voiceflow.ui.overlay import RecordingOverlay
from voiceflow.ui.tray import TrayManager


class VoiceFlowApp:
    def __init__(self, qt_app: QApplication):
        self._qt_app = qt_app
        qt_app.setQuitOnLastWindowClosed(False)

        self._settings = SettingsManager()
        cfg = self._settings.config

        qt_app.setStyleSheet(vf_theme.build_stylesheet(cfg.theme))

        self._db = HistoryDB(cfg.turso_db_url, cfg.turso_auth_token)
        self._pipeline = Pipeline(self._settings, self._db)

        self._window = MainWindow(self._settings, self._db, self._pipeline)
        self._overlay = RecordingOverlay()
        self._tray = TrayManager(qt_app, self._window, self._pipeline)

        self._window.show()
        if cfg.first_run:
            self._settings.set("first_run", False)

        self._pipeline.state_changed.connect(self._on_state_changed)
        self._pipeline.error_occurred.connect(self._tray.notify_error)
        self._pipeline.recorder.level_updated.connect(self._overlay.set_level)

        self._window.theme_changed.connect(self._on_theme_changed)

        if cfg.theme != "dark":
            self._window.set_theme(cfg.theme)

    def _on_state_changed(self, state: State):
        if state == State.RECORDING:
            self._overlay.show_recording()
        elif state in (State.TRANSCRIBING, State.PROCESSING):
            self._overlay.show_processing()
        else:
            self._overlay.hide_overlay()

    def _on_theme_changed(self, new_theme: str):
        vf_theme.set_active(new_theme)
        self._qt_app.setStyleSheet(vf_theme.build_stylesheet(new_theme))
        self._overlay.set_theme(new_theme)

    def shutdown(self):
        self._pipeline.shutdown()
