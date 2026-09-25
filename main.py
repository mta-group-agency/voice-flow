import os
import platform
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

import voiceflow.core.logger as logger
from voiceflow.__version__ import __version__
from voiceflow.app import VoiceFlowApp
from voiceflow.config.settings_manager import SettingsManager
from voiceflow.platform import (
    DATA_DIR_DISPLAY, IS_MAC, ensure_single_instance, prepare_qt_env,
    show_startup_permission_hint,
)

_STT_MODEL_FIELD = {"gemini": "stt_model", "groq": "groq_stt_model", "local": "local_whisper_model"}
_AI_MODEL_FIELD = {"gemini": "gemini_ai_model", "claude": "claude_ai_model", "groq": "groq_ai_model"}
_ASSISTANT_MODEL_FIELD = {
    "gemini": "assistant_gemini_model", "claude": "assistant_claude_model", "groq": "assistant_groq_model",
}


def _app_icon() -> QIcon:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    if IS_MAC:
        return QIcon(os.path.join(base, "assets", "common", "icon.png"))
    return QIcon(os.path.join(base, "assets", "windows", "icon.ico"))


def _model_for(cfg, mapping: dict, provider) -> str | None:
    # provider comes straight from config.json; an odd/hand-edited value (list, dict,
    # non-str) must not blow up the startup log — just show no model for it.
    if not isinstance(provider, str):
        return None
    field = mapping.get(provider)
    return getattr(cfg, field, None) if field else None


def _log_version(log, log_file) -> None:
    log_name = f"{DATA_DIR_DISPLAY}{os.sep}{log_file.name}" if log_file else "none"
    log.info(
        "VoiceFlow %s starting (python=%s, windows=%s, frozen=%s, log=%s)",
        __version__, platform.python_version(), platform.platform(),
        bool(getattr(sys, "frozen", False)), log_name,
    )


def _log_active_providers(log, cfg) -> None:
    assistant_provider = cfg.assistant_model_provider or cfg.ai_model_provider
    log.info(
        "Active providers: stt=%s/%s, ai=%s/%s, assistant=%s/%s",
        cfg.stt_provider, _model_for(cfg, _STT_MODEL_FIELD, cfg.stt_provider),
        cfg.ai_model_provider, _model_for(cfg, _AI_MODEL_FIELD, cfg.ai_model_provider),
        assistant_provider, _model_for(cfg, _ASSISTANT_MODEL_FIELD, assistant_provider),
    )


def main():
    # Before any QApplication, including the one ensure_single_instance may create on macOS.
    prepare_qt_env()
    _instance_lock = ensure_single_instance()

    log_file = logger.setup()
    log = logger.get("main")
    _log_version(log, log_file)

    app = QApplication(sys.argv)
    app.setApplicationName("VoiceFlow")
    app.setApplicationVersion(__version__)
    app.setWindowIcon(_app_icon())

    try:
        settings = SettingsManager()
        _log_active_providers(log, settings.config)
        vf = VoiceFlowApp(app, settings=settings)
    except Exception:
        log.critical("Failed to initialize VoiceFlowApp", exc_info=True)
        sys.exit(1)

    QTimer.singleShot(0, show_startup_permission_hint)
    exit_code = app.exec()
    log.info("VoiceFlow shutting down (exit code %d)", exit_code)
    vf.shutdown()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
