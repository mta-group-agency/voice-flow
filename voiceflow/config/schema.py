from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProcessingConfig:
    remove_fillers: bool = False
    fix_grammar: bool = False
    translation_target: Optional[str] = None
    tone: Optional[str] = None
    intensity: int = 3
    custom_prompt: str = ""


@dataclass
class AppConfig:
    # API Keys
    gemini_api_key: str = ""
    claude_api_key: str = ""
    groq_api_key: str = ""

    # Database (Turso)
    turso_enabled: bool = False
    turso_db_url: str = ""
    turso_auth_token: str = ""

    # STT provider + models
    stt_provider: str = "groq"                # "gemini" | "groq" | "local"
    stt_model: str = "gemini-2.5-flash"       # Gemini STT model
    groq_stt_model: str = "whisper-large-v3-turbo"
    local_whisper_model: str = "small"        # "tiny"|"small"|"medium"|"large-v3"

    # AI text processing
    ai_model_provider: str = "groq"           # "gemini" | "claude" | "groq"
    gemini_ai_model: str = "gemini-2.5-flash"
    claude_ai_model: str = "claude-sonnet-5"
    groq_ai_model: str = "openai/gpt-oss-120b"

    # Hotkey (pynput key string)
    hotkey: str = "Key.alt_r"
    hotkey_assistant: str = ""

    # AI assistant mode (second hotkey track)
    assistant_use_clipboard: bool = True
    assistant_model_provider: str = ""   # "" = use ai_model_provider; else "gemini"|"claude"|"groq"
    assistant_gemini_model: str = "gemini-2.5-flash"
    assistant_claude_model: str = "claude-sonnet-5"
    assistant_groq_model: str = "openai/gpt-oss-120b"
    assistant_prompt: str = (
        "Jesteś asystentem piszącym po polsku. Wykonaj polecenie użytkownika i zwróć "
        "WYŁĄCZNIE gotowy tekst do wklejenia — bez wstępów, komentarzy, wyjaśnień ani "
        "znaczników formatowania. Jeśli dołączono kontekst (zaznaczony lub skopiowany "
        "tekst), użyj go tylko wtedy, gdy polecenie wyraźnie się do niego odnosi."
    )

    # Audio
    audio_device_index: Optional[int] = None
    sample_rate: int = 16000

    # AI feature toggles
    # Off by default: a fresh install should dictate with plain Whisper immediately
    # on a Groq key alone, no second (AI text) key required. See SettingsManager's
    # _LEGACY_DEFAULTS for why an existing config.json is unaffected by this.
    ai_processing_enabled: bool = False
    ai_custom_prompt: str = ""
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
    last_run_version: str = ""
    pending_update_version: str = ""
    pending_update_notes: str = ""
    pending_update_video: str = ""
