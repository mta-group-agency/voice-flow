import ctypes
import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

import voiceflow.core.logger as logger
from voiceflow.__version__ import __version__
from voiceflow.app import VoiceFlowApp


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
    return QIcon(os.path.join(base, "assets", "icon.ico"))


def main():
    _mutex = _ensure_single_instance()

    log_file = logger.setup()
    log = logger.get("main")
    log.info("VoiceFlow starting — log: %s", log_file)

    app = QApplication(sys.argv)
    app.setApplicationName("VoiceFlow")
    app.setApplicationVersion(__version__)
    app.setWindowIcon(_app_icon())

    try:
        vf = VoiceFlowApp(app)
    except Exception:
        log.critical("Failed to initialize VoiceFlowApp", exc_info=True)
        sys.exit(1)

    exit_code = app.exec()
    log.info("VoiceFlow shutting down (exit code %d)", exit_code)
    vf.shutdown()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
