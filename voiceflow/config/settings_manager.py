import json
import os
from dataclasses import asdict, fields
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from voiceflow.config.schema import AppConfig


class SettingsManager(QObject):
    settings_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._config = AppConfig()
        self._path = self._resolve_path()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.load()

    def _resolve_path(self) -> Path:
        appdata = os.environ.get("APPDATA", str(Path.home()))
        return Path(appdata) / "VoiceFlow" / "config.json"

    _MODEL_MIGRATIONS = {
        "gemini-2.0-flash": "gemini-2.5-flash",
        "gemini-2.0-flash-exp": "gemini-2.5-flash",
        "gemini-1.5-flash": "gemini-2.5-flash",
        "gemini-1.5-flash-8b": "gemini-2.5-flash-lite",
        "gemini-1.5-pro": "gemini-2.5-pro",
    }

    def load(self):
        if not self._path.exists():
            self.save()
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            valid_keys = {f.name for f in fields(AppConfig)}
            filtered = {k: v for k, v in data.items() if k in valid_keys}
            for key in ("stt_model", "gemini_ai_model"):
                if key in filtered:
                    filtered[key] = self._MODEL_MIGRATIONS.get(filtered[key], filtered[key])
            self._config = AppConfig(**filtered)
        except Exception:
            self._config = AppConfig()
            self.save()

    def save(self):
        self._path.write_text(
            json.dumps(asdict(self._config), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get(self, key: str):
        return getattr(self._config, key)

    def set(self, key: str, value):
        if not hasattr(self._config, key):
            raise KeyError(f"Unknown config key: {key}")
        setattr(self._config, key, value)
        self.save()
        self.settings_changed.emit(key)

    @property
    def config(self) -> AppConfig:
        return self._config
