import sys

from PyQt6.QtWidgets import QApplication

import voiceflow.core.logger as logger
from voiceflow.app import VoiceFlowApp


def main():
    log_file = logger.setup()
    log = logger.get("main")
    log.info("VoiceFlow starting — log: %s", log_file)

    app = QApplication(sys.argv)
    app.setApplicationName("VoiceFlow")
    app.setApplicationVersion("1.0.0")

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
