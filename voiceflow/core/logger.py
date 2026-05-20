import logging
import os
import sys
from pathlib import Path


def setup() -> Path:
    log_dir = Path(os.environ.get("APPDATA", Path.home())) / "VoiceFlow"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "voiceflow.log"

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8")],
    )

    def excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logging.getLogger("uncaught").critical(
            "Unhandled exception", exc_info=(exc_type, exc_value, exc_tb)
        )

    sys.excepthook = excepthook
    return log_file


def get(name: str) -> logging.Logger:
    return logging.getLogger(name)
