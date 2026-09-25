import json
from dataclasses import asdict, fields
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from voiceflow.config.schema import AppConfig
from voiceflow.platform import data_dir


class SettingsManager(QObject):
    settings_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._config = AppConfig()
        self._path = self._resolve_path()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.last_migrations: list[tuple[str, str, str]] = []
        self.load()

    def _resolve_path(self) -> Path:
        return data_dir() / "config.json"

    _MODEL_MIGRATIONS = {
        "gemini-2.0-flash": "gemini-2.5-flash",
        "gemini-2.0-flash-exp": "gemini-2.5-flash",
        "gemini-1.5-flash": "gemini-2.5-flash",
        "gemini-1.5-flash-8b": "gemini-2.5-flash-lite",
        "gemini-1.5-pro": "gemini-2.5-flash",
        "gemini-2.5-pro": "gemini-2.5-flash",
        "llama-3.3-70b-versatile": "openai/gpt-oss-120b",
        "llama-3.1-8b-instant": "openai/gpt-oss-120b",
        "mixtral-8x7b-32768": "openai/gpt-oss-120b",
    }

    # Fields whose class-level default changed when STT-only-by-default onboarding
    # shipped (schema.py). save() always dumps the full dataclass, so any config.json
    # that was ever saved by that or a later version already has these keys explicit
    # — this fallback only fires for a file that predates the field's introduction and
    # would otherwise silently inherit the new default instead of the user's real,
    # previously-implicit one (AI processing on, Gemini as provider).
    _LEGACY_DEFAULTS = {
        "ai_processing_enabled": True,
        "stt_provider": "gemini",
        "ai_model_provider": "gemini",
    }

    def load(self):
        self.last_migrations = []
        if not self._path.exists():
            self.save()
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            valid_keys = {f.name for f in fields(AppConfig)}
            filtered = {k: v for k, v in data.items() if k in valid_keys}
            for key, legacy_value in self._LEGACY_DEFAULTS.items():
                if key not in filtered:
                    filtered[key] = legacy_value
            for key in (
                "stt_model", "gemini_ai_model", "assistant_gemini_model",
                "groq_ai_model", "assistant_groq_model",
            ):
                if key in filtered:
                    old = filtered[key]
                    new = self._MODEL_MIGRATIONS.get(old, old)
                    if new != old:
                        self.last_migrations.append((key, old, new))
                    filtered[key] = new
            self._config = AppConfig(**filtered)
            if self.last_migrations:
                self.save()
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
