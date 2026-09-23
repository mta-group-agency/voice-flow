"""
VoiceFlow application bootstrap.
"""

from PyQt6.QtWidgets import QApplication, QDialog

from voiceflow.__version__ import __version__
from voiceflow.config import model_healing
from voiceflow.config.settings_manager import SettingsManager
from voiceflow.core.pipeline import Pipeline, State
from voiceflow.storage.history_db import HistoryDB
from voiceflow.ui import theme as vf_theme
from voiceflow.ui.main_window import MainWindow
from voiceflow.ui.model_discovery import ModelDiscoveryWorker
from voiceflow.ui.overlay import RecordingOverlay
from voiceflow.ui.tray import TrayManager
from voiceflow.ui.update_banner import ReleaseNotesWorker, UpdateCheckWorker
from voiceflow.ui.whats_new_dialog import (
    WELCOME_BODY, WELCOME_TITLE, WELCOME_VIDEO_URL, WhatsNewDialog,
)

_RELEASES_URL = "https://github.com/mta-group-agency/voice-flow/releases"

# Config field -> the Settings section a user would recognize and go fix, so a healing
# toast can point at "AI Assistant" instead of a raw config key name.
_HEALED_FIELD_FEATURES = {
    "stt_model": "Speech-to-Text",
    "groq_stt_model": "Speech-to-Text",
    "gemini_ai_model": "AI Text Processing",
    "claude_ai_model": "AI Text Processing",
    "groq_ai_model": "AI Text Processing",
    "assistant_gemini_model": "AI Assistant",
    "assistant_claude_model": "AI Assistant",
    "assistant_groq_model": "AI Assistant",
}


def _heal_feature_name(field: str) -> str:
    return _HEALED_FIELD_FEATURES.get(field, field)


def _heal_notification_body(
    provider: str, healed: list[tuple[str, str, str]], ai_processing_enabled: bool = True
) -> str:
    """One short toast body, built around feature names instead of raw model ids.
    Kept as a module function (not a method) so it stays callable with any object
    standing in for the app in a test harness."""
    provider_name = provider.capitalize()

    # A feature the user has switched off is noise, not news — drop it before deciding
    # how much the toast needs to say.
    visible = [
        (field, old, new) for field, old, new in healed
        if ai_processing_enabled or _heal_feature_name(field) != "AI Text Processing"
    ]
    if not visible:
        old, new = healed[0][1], healed[0][2]
        return f"{provider_name} discontinued {old}, switched to {new}."

    distinct_pairs = sorted({(old, new) for _, old, new in visible})
    features = sorted({_heal_feature_name(field) for field, _, _ in visible})

    if len(distinct_pairs) == 1:
        old, new = distinct_pairs[0]
        feature = " & ".join(features)
        if len(features) == 1:
            return (
                f"{provider_name} discontinued {old}. {feature} now uses {new}. "
                f"Change it in Settings → {feature}."
            )
        return f"{provider_name} discontinued {old}. {feature} now use {new}. See Settings for details."

    parts = ", ".join(f"{_heal_feature_name(field)} → {new}" for field, old, new in visible)
    return f"{provider_name} updated {len(visible)} models: {parts}. See Settings for details."


class VoiceFlowApp:
    def __init__(self, qt_app: QApplication):
        self._qt_app = qt_app
        qt_app.setQuitOnLastWindowClosed(False)

        self._settings = SettingsManager()
        cfg = self._settings.config

        qt_app.setStyleSheet(vf_theme.build_stylesheet(cfg.theme))

        self._db = HistoryDB(
            cfg.turso_db_url if cfg.turso_enabled else "",
            cfg.turso_auth_token if cfg.turso_enabled else "",
        )
        self._pipeline = Pipeline(self._settings, self._db)

        self._window = MainWindow(self._settings, self._db, self._pipeline)
        self._overlay = RecordingOverlay()
        self._tray = TrayManager(qt_app, self._window, self._pipeline)

        # The static migration table only ever covers Gemini fields and is a blind,
        # offline fallback. When the Gemini key is present, the live model-discovery
        # notification below is authoritative — sending both would double-toast the
        # same startup.
        if self._settings.last_migrations and not cfg.gemini_api_key:
            pairs = sorted({(old, new) for _, old, new in self._settings.last_migrations})
            changes = ", ".join(f'"{old}" -> "{new}"' for old, new in pairs)
            self._tray.notify(
                "VoiceFlow — AI model updated",
                f"A discontinued provider model was detected and switched to a current one: {changes}.",
            )

        self._window.show()
        self._run_onboarding(cfg)

        self._pipeline.state_changed.connect(self._on_state_changed)
        self._pipeline.error_occurred.connect(self._tray.notify_error)
        self._pipeline.recorder.level_updated.connect(self._overlay.set_level)
        self._overlay.cancel_requested.connect(self._pipeline.cancel)

        self._window.theme_changed.connect(self._on_theme_changed)

        if cfg.theme != "dark":
            self._window.set_theme(cfg.theme)

        self._window.connect_restart(self._qt_app.quit)
        self._update_worker = UpdateCheckWorker()
        self._update_worker.update_found.connect(self._on_update_found)
        self._update_worker.start()

        self._model_worker = ModelDiscoveryWorker(
            cfg.gemini_api_key, cfg.claude_api_key, cfg.groq_api_key,
        )
        self._model_worker.provider_models_ready.connect(self._on_models_discovered)
        self._model_worker.start()

    def _on_state_changed(self, state: State):
        if state == State.RECORDING:
            self._overlay.set_assistant_mode(self._pipeline.mode == "assistant")
            self._overlay.show_recording()
        elif state in (State.TRANSCRIBING, State.PROCESSING):
            self._overlay.show_processing()
        else:
            self._overlay.hide_overlay()

    def _run_onboarding(self, cfg):
        if cfg.first_run:
            self._settings.set("first_run", False)
            WhatsNewDialog(
                WELCOME_TITLE, WELCOME_BODY, WELCOME_VIDEO_URL or None,
                mode="welcome", parent=self._window,
            ).exec()
        elif cfg.last_run_version and cfg.last_run_version != __version__:
            if cfg.pending_update_version == __version__ and cfg.pending_update_notes:
                body = cfg.pending_update_notes
                video = cfg.pending_update_video or None
                WhatsNewDialog(
                    f"Zaktualizowano do {__version__} — co nowego", body, video,
                    mode="post_update", parent=self._window,
                ).exec()
            else:
                self._notes_worker = ReleaseNotesWorker(__version__)
                self._notes_worker.notes_ready.connect(self._on_release_notes)
                self._notes_worker.start()

            self._settings.set("pending_update_version", "")
            self._settings.set("pending_update_notes", "")
            self._settings.set("pending_update_video", "")

        self._settings.set("last_run_version", __version__)

    def _on_release_notes(self, body, video):
        if body:
            WhatsNewDialog(
                f"Zaktualizowano do {__version__} — co nowego", body, video,
                mode="post_update", parent=self._window,
            ).exec()
        else:
            fallback = (
                f"Zaktualizowano do {__version__}. "
                f"Zobacz szczegóły wydania na [GitHub]({_RELEASES_URL})."
            )
            WhatsNewDialog(
                f"Zaktualizowano do {__version__} — co nowego", fallback,
                mode="post_update", parent=self._window,
            ).exec()

    def _on_update_found(self, info):
        self._window.show_update_banner(info)
        self._tray.notify_update(info)

        body = info.body or f"Nowa wersja {info.latest_version} jest dostępna."
        dialog = WhatsNewDialog(
            f"Nowa wersja {info.latest_version}", body, info.video_url,
            mode="pre_update", parent=self._window,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._window.trigger_update()

    def _on_models_discovered(self, provider: str, payload):
        if isinstance(payload, dict):
            buckets = [("stt", payload.get("stt", [])), ("chat", payload.get("chat", []))]
        else:
            buckets = [("stt", payload), ("chat", payload)] if provider == "gemini" else [("chat", payload)]

        healed = []
        for kind, available in buckets:
            for field, old, new in model_healing.heal_config(self._settings.config, provider, kind, available):
                self._settings.set(field, new)
                healed.append((field, old, new))

        if healed:
            self._tray.notify(
                "VoiceFlow — AI model updated",
                _heal_notification_body(provider, healed, self._settings.config.ai_processing_enabled),
            )

        self._window.apply_discovered_models(
            provider, payload, healed={field: old for field, old, new in healed}
        )

    def _on_theme_changed(self, new_theme: str):
        vf_theme.set_active(new_theme)
        self._qt_app.setStyleSheet(vf_theme.build_stylesheet(new_theme))
        self._overlay.set_theme(new_theme)

    def shutdown(self):
        self._pipeline.shutdown()
