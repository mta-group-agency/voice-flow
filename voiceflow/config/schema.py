from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProcessingConfig:
    remove_fillers: bool = True
    fix_grammar: bool = True
    translation_target: Optional[str] = None
    tone: Optional[str] = None
    intensity: int = 3  # 1=light, 3=balanced, 5=aggressive


@dataclass
class AppConfig:
    # API Keys
    gemini_api_key: str = ""
    claude_api_key: str = ""
    groq_api_key: str = ""

    # Database (Turso)
    turso_db_url: str = ""
    turso_auth_token: str = ""

    # STT provider + models
    stt_provider: str = "gemini"              # "gemini" | "groq" | "local"
    stt_model: str = "gemini-2.5-flash"       # Gemini STT model
    groq_stt_model: str = "whisper-large-v3-turbo"
    local_whisper_model: str = "small"        # "tiny"|"small"|"medium"|"large-v3"

    # AI text processing
    ai_model_provider: str = "gemini"         # "gemini" | "claude" | "groq"
    gemini_ai_model: str = "gemini-2.5-flash"
    claude_ai_model: str = "claude-sonnet-4-6"
    groq_ai_model: str = "llama-3.3-70b-versatile"

    # Hotkey (pynput key string)
    hotkey: str = "Key.alt_r"

    # Audio
    audio_device_index: Optional[int] = None
    sample_rate: int = 16000

    # AI feature toggles
    remove_fillers: bool = True
    fix_grammar: bool = True
    auto_translate: bool = False
    translation_language: str = "English"
    tone_adjustment_enabled: bool = False
    tone_adjustment_value: str = "formal"
    ai_intensity: int = 3  # 1=light touch, 3=balanced, 5=aggressive

    # UI
    theme: str = "dark"
    show_overlay: bool = True
    overlay_x_pct: int = 95
    overlay_y_pct: int = 90

    # App meta
    first_run: bool = True
    version: str = "1.0.0"
