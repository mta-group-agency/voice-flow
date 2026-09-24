import ctypes
import os
import platform
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

import voiceflow.core.logger as logger
from voiceflow.__version__ import __version__
from voiceflow.app import VoiceFlowApp
from voiceflow.config.settings_manager import SettingsManager

_STT_MODEL_FIELD = {"gemini": "stt_model", "groq": "groq_stt_model", "local": "local_whisper_model"}
_AI_MODEL_FIELD = {"gemini": "gemini_ai_model", "claude": "claude_ai_model", "groq": "groq_ai_model"}
_ASSISTANT_MODEL_FIELD = {
    "gemini": "assistant_gemini_model", "claude": "assistant_claude_model", "groq": "assistant_groq_model",
}


def _ensure_single_instance():
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, "VoiceFlow_SingleInstance_Mutex")
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        ctypes.windll.user32.MessageBoxW(
            0,
            "VoiceFlow is already running.\nCheck the system tray.",
            "VoiceFlow",
            0x40,  # MB_ICONINFORMATION
        )
        sys.exit(0)
    return mutex


def _app_icon() -> QIcon:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return QIcon(os.path.join(base, "assets", "windows", "icon.ico"))


def _model_for(cfg, mapping: dict, provider) -> str | None:
    # provider comes straight from config.json; an odd/hand-edited value (list, dict,
    # non-str) must not blow up the startup log — just show no model for it.
    if not isinstance(provider, str):
        return None
    field = mapping.get(provider)
    return getattr(cfg, field, None) if field else None


def _log_version(log, log_file) -> None:
    log_name = f"%APPDATA%\\VoiceFlow\\{log_file.name}" if log_file else "none"
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
    _mutex = _ensure_single_instance()

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

    exit_code = app.exec()
    log.info("VoiceFlow shutting down (exit code %d)", exit_code)
    vf.shutdown()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
