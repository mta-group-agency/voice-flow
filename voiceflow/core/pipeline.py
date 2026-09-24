"""
Central pipeline orchestrator.
State machine: IDLE → RECORDING → TRANSCRIBING → PROCESSING → INJECTING → IDLE
"""

from __future__ import annotations

import re
import time
from enum import Enum, auto
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, QTimer, pyqtSignal, pyqtSlot

from voiceflow.api.claude_client import ClaudeClient
from voiceflow.api.gemini_client import GeminiClient
from voiceflow.api.groq_client import GroqClient
from voiceflow.api.local_whisper_client import LocalWhisperClient
from voiceflow.config.schema import ProcessingConfig
from voiceflow.core.audio_recorder import AudioRecorder
from voiceflow.core.hotkey_manager import HotkeyManager
from voiceflow.core import logger
from voiceflow.core.text_injector import TextInjector
from voiceflow.storage.history_db import HistoryDB, TranscriptionEntry

if TYPE_CHECKING:
    from voiceflow.config.settings_manager import SettingsManager

_log = logger.get("pipeline")

_TRANSLATE_RE = re.compile(r"^translate\s+to\s+(\w+)[\s:,]+(.+)$", re.IGNORECASE | re.DOTALL)
_MIN_AUDIO_DURATION = 0.3  # seconds
_MODE_DICTATION = "dictation"
_MODE_ASSISTANT = "assistant"
_ASSISTANT_CONTEXT_LIMIT = 8000
# Fallback order when a provider is inherited/default and has no key — groq first,
# since the free tier is this project's default track. Shared by the assistant and
# dictation post-processing (both can use any of the three providers).
_PROVIDER_FALLBACK_ORDER = ("groq", "gemini", "claude")
# Same idea for speech-to-text, which only groq and gemini support in this app —
# ClaudeClient.transcribe() raises NotImplementedError.
_STT_PROVIDER_FALLBACK = ("groq", "gemini")


class State(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()
    PROCESSING = auto()
    INJECTING = auto()


class _Worker(QRunnable):
    def __init__(self, fn, *args, on_result=None, on_error=None):
        super().__init__()
        self._fn = fn
        self._args = args
        self._on_result = on_result
        self._on_error = on_error
        self.setAutoDelete(True)

    def run(self):
        try:
            result = self._fn(*self._args)
            if self._on_result:
                self._on_result(result)
        except Exception as e:
            if self._on_error:
                self._on_error(e)


class Pipeline(QObject):
    state_changed = pyqtSignal(object)        # State enum value
    transcription_ready = pyqtSignal(str)     # final_text after AI processing
    error_occurred = pyqtSignal(str)          # human-readable error message
    history_updated = pyqtSignal()            # after DB insert
    _inject_ready = pyqtSignal(str, str, float)  # raw_text, final_text, cost — main-thread bridge

    def __init__(self, settings: "SettingsManager", db: HistoryDB):
        super().__init__()
        self._settings = settings
        self._db = db
        self._state = State.IDLE
        self._pool = QThreadPool.globalInstance()
        self._recording_start: float = 0.0
        self._last_wav: bytes = b""
        self._cancel_flag: bool = False
        self._mode: str = _MODE_DICTATION
        self._assistant_context: str | None = None
        # Context for the in-flight worker (step/provider/model/…), read by _on_error
        # and the cancel/timeout path — never shown to the user, log-only.
        self._run_ctx: dict = {}
        # What actually ran this cycle, for the one-line success summary — reset per
        # recording so a skipped step doesn't carry over stale data from the last one.
        self._stt_provider: str | None = None
        self._stt_model: str | None = None
        self._ai_provider: str | None = None
        self._ai_model: str | None = None

        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.setInterval(30_000)
        self._timeout_timer.timeout.connect(self._on_timeout)

        cfg = settings.config
        self._recorder = AudioRecorder(
            sample_rate=cfg.sample_rate,
            device_index=cfg.audio_device_index,
        )
        self._hotkey = HotkeyManager(cfg.hotkey)
        self._hotkey_assistant = HotkeyManager(cfg.hotkey_assistant)
        self._injector = TextInjector(
            hotkey_managers=[self._hotkey, self._hotkey_assistant]
        )

        self._hotkey.hotkey_pressed.connect(self._on_hotkey_pressed)
        self._hotkey.hotkey_released.connect(self._on_hotkey_released)
        self._hotkey.cancel_pressed.connect(self._on_cancel_pressed)
        self._hotkey_assistant.hotkey_pressed.connect(self._on_assistant_hotkey_pressed)
        self._hotkey_assistant.hotkey_released.connect(self._on_hotkey_released)
        self._hotkey_assistant.cancel_pressed.connect(self._on_cancel_pressed)
        self._recorder.recording_finished.connect(self._on_recording_finished)
        self._inject_ready.connect(self._on_inject_ready)

        self._hotkey.start()
        self._hotkey_assistant.start()

    # ── public API ──────────────────────────────────────────────────────────

    def cancel(self, timed_out: bool = False):
        if self._state not in (State.TRANSCRIBING, State.PROCESSING):
            return
        self._cancel_flag = True
        self._timeout_timer.stop()
        self._set_state(State.IDLE)
        step, provider, model = (
            self._run_ctx.get("step", "?"), self._run_ctx.get("provider"), self._run_ctx.get("model"),
        )
        if timed_out:
            _log.warning("Timed out after 30s (step=%s, provider=%s, model=%s)", step, provider, model)
            msg = "Processing timed out after 30s — cancelled automatically."
        else:
            _log.info("Cancelled by user (step=%s, provider=%s, model=%s)", step, provider, model)
            msg = "Cancelled."
        self.error_occurred.emit(msg)

    def reconfigure(self):
        cfg = self._settings.config
        self._hotkey.reconfigure(cfg.hotkey)
        self._hotkey_assistant.reconfigure(cfg.hotkey_assistant)
        self._recorder.sample_rate = cfg.sample_rate
        self._recorder.device_index = cfg.audio_device_index
        if cfg.turso_enabled:
            self._db.reconfigure(cfg.turso_db_url, cfg.turso_auth_token)
        else:
            self._db.reconfigure("", "")

    def shutdown(self):
        self._hotkey.stop()
        self._hotkey_assistant.stop()
        if self._recorder.isRunning():
            self._recorder.stop_recording()
            self._recorder.wait(2000)

    @property
    def state(self) -> State:
        return self._state

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def recorder(self) -> AudioRecorder:
        return self._recorder

    # ── private helpers ──────────────────────────────────────────────────────

    def _on_timeout(self):
        self.cancel(timed_out=True)

    def _set_state(self, state: State):
        self._state = state
        self.state_changed.emit(state)
        if state == State.RECORDING:
            self._cancel_flag = False
        elif state == State.TRANSCRIBING:
            self._timeout_timer.start()
        elif state in (State.IDLE, State.INJECTING):
            self._timeout_timer.stop()

    def _make_gemini(self, for_assistant: bool = False) -> GeminiClient:
        cfg = self._settings.config
        ai_model = cfg.assistant_gemini_model if for_assistant else cfg.gemini_ai_model
        return GeminiClient(cfg.gemini_api_key, cfg.stt_model, ai_model)

    def _make_claude(self, for_assistant: bool = False) -> ClaudeClient:
        cfg = self._settings.config
        ai_model = cfg.assistant_claude_model if for_assistant else cfg.claude_ai_model
        return ClaudeClient(cfg.claude_api_key, ai_model)

    def _make_groq(self, for_assistant: bool = False) -> GroqClient:
        cfg = self._settings.config
        ai_model = cfg.assistant_groq_model if for_assistant else cfg.groq_ai_model
        return GroqClient(cfg.groq_api_key, cfg.groq_stt_model, ai_model)

    def _resolve_stt_provider(self) -> str | None:
        """Configured provider if it has a key; else the first of groq/gemini that does
        (groq first — the free tier is this project's default track); else None.
        "local" needs no key and passes straight through untouched."""
        cfg = self._settings.config
        if cfg.stt_provider == "local":
            return "local"
        keys = {"groq": cfg.groq_api_key, "gemini": cfg.gemini_api_key}
        if keys.get(cfg.stt_provider):
            return cfg.stt_provider
        return next((p for p in _STT_PROVIDER_FALLBACK if keys.get(p)), None)

    def _resolve_text_provider(self) -> str | None:
        """Same cascade as _resolve_stt_provider, for dictation post-processing —
        configured provider if it has a key, else the first of groq/gemini/claude
        that does; else None."""
        cfg = self._settings.config
        keys = {"groq": cfg.groq_api_key, "gemini": cfg.gemini_api_key, "claude": cfg.claude_api_key}
        if keys.get(cfg.ai_model_provider):
            return cfg.ai_model_provider
        return next((p for p in _PROVIDER_FALLBACK_ORDER if keys.get(p)), None)

    def _make_stt_client(self):
        provider = self._resolve_stt_provider()
        if provider == "local":
            return LocalWhisperClient(self._settings.config.local_whisper_model)
        if provider == "groq":
            return self._make_groq()
        if provider == "gemini":
            return self._make_gemini()
        return None

    def _emit_error(self, user_message: str, log_message: str, *log_args) -> None:
        _log.warning(log_message, *log_args)
        self.error_occurred.emit(user_message)

    def _build_processing_config(self, raw_text: str) -> tuple[str, ProcessingConfig]:
        cfg = self._settings.config

        if not cfg.ai_processing_enabled:
            return raw_text, ProcessingConfig()

        text = raw_text

        # Check for translation voice command
        translation_target = None
        m = _TRANSLATE_RE.match(raw_text.strip())
        if m:
            translation_target = m.group(1).strip().capitalize()
            text = m.group(2).strip()
        elif cfg.auto_translate:
            translation_target = cfg.translation_language

        custom_prompt = cfg.ai_custom_prompt.strip() if cfg.ai_custom_prompt else ""
        proc = ProcessingConfig(
            remove_fillers=cfg.remove_fillers if not custom_prompt else False,
            fix_grammar=cfg.fix_grammar if not custom_prompt else False,
            translation_target=translation_target,
            tone=cfg.tone_adjustment_value if cfg.tone_adjustment_enabled else None,
            intensity=cfg.ai_intensity,
            custom_prompt=custom_prompt,
        )
        return text, proc

    # ── slots ────────────────────────────────────────────────────────────────

    @pyqtSlot()
    def _on_cancel_pressed(self):
        self.cancel()

    @pyqtSlot()
    def _on_hotkey_pressed(self):
        if self._state != State.IDLE:
            return
        self._mode = _MODE_DICTATION
        self._assistant_context = None
        self._reset_run_tracking()
        self._set_state(State.RECORDING)
        self._recording_start = time.time()
        self._recorder.start_recording()

    @pyqtSlot()
    def _on_assistant_hotkey_pressed(self):
        if self._state != State.IDLE:
            return
        self._mode = _MODE_ASSISTANT
        self._assistant_context = self._read_clipboard_context()
        self._reset_run_tracking()
        self._set_state(State.RECORDING)
        self._recording_start = time.time()
        self._recorder.start_recording()

    def _reset_run_tracking(self) -> None:
        self._run_ctx = {}
        self._stt_provider = self._stt_model = None
        self._ai_provider = self._ai_model = None

    def _read_clipboard_context(self) -> str | None:
        # Must run on the main Qt thread (called from the hotkey-press slot).
        if not self._settings.config.assistant_use_clipboard:
            return None
        from PyQt6.QtWidgets import QApplication
        text = QApplication.clipboard().text()
        if not text or not text.strip():
            return None
        return text[:_ASSISTANT_CONTEXT_LIMIT]

    @pyqtSlot()
    def _on_hotkey_released(self):
        if self._state != State.RECORDING:
            return
        self._set_state(State.TRANSCRIBING)
        self._recorder.stop_recording()

    @pyqtSlot(bytes)
    def _on_recording_finished(self, wav_bytes: bytes):
        # Ignore a result that arrives outside the transcription window (e.g. a
        # stale emit from a previous capture thread after a fast double-tap).
        if self._state != State.TRANSCRIBING:
            return

        duration = time.time() - self._recording_start
        if duration < _MIN_AUDIO_DURATION or not wav_bytes:
            self._set_state(State.IDLE)
            self._emit_error(
                "Recording too short — hold the key and speak.",
                "Recording too short (duration=%.2fs, has_audio=%s)", duration, bool(wav_bytes),
            )
            return

        self._last_wav = wav_bytes
        self._last_duration = duration

        _, proc_config = self._build_processing_config("")
        any_feature = bool(
            proc_config.remove_fillers or proc_config.fix_grammar
            or proc_config.translation_target or proc_config.tone
        )
        stt_provider = self._resolve_stt_provider()
        text_provider = self._resolve_text_provider() if any_feature else None
        # Combined Gemini call only when both STT and AI processing actually resolve
        # to Gemini — checked against the resolved provider, not the raw config, so a
        # cascade to another provider can't be bypassed by this shortcut. Assistant
        # mode always transcribes separately so the raw command is available for the
        # assistant call.
        use_combined = (
            self._mode == _MODE_DICTATION
            and any_feature
            and stt_provider == "gemini"
            and text_provider == "gemini"
        )
        audio_s = duration

        if use_combined:
            gemini = self._make_gemini()
            self._stt_provider = self._ai_provider = "gemini"
            self._stt_model = gemini.stt_model
            self._ai_model = gemini.ai_model
            self._run_ctx = {"step": "combined", "provider": "gemini", "model": gemini.stt_model, "audio_s": audio_s}

            def _combined():
                final = gemini.transcribe_and_process(wav_bytes, proc_config)
                cost = GeminiClient.estimate_cost(audio_s, len(final))
                return final, cost

            worker = _Worker(
                _combined,
                on_result=lambda r: self._on_ai_done(raw_text=r[0], final_text=r[0], cost=r[1]),
                on_error=self._on_error,
            )
        else:
            stt = self._make_stt_client()
            if stt is None:
                self._set_state(State.IDLE)
                self._emit_error(
                    "No API key configured for speech-to-text. Add one in Settings → API Keys.",
                    "No STT API key configured (configured_provider=%s)", self._settings.config.stt_provider,
                )
                return
            self._stt_provider = stt_provider
            self._stt_model = getattr(stt, "stt_model", None)
            self._run_ctx = {"step": "transcribe", "provider": stt_provider, "model": self._stt_model, "audio_s": audio_s}
            worker = _Worker(
                stt.transcribe,
                wav_bytes,
                on_result=self._on_transcription_done,
                on_error=self._on_error,
            )
        self._pool.start(worker)

    def _on_transcription_done(self, raw_text: str):
        if self._cancel_flag:
            return
        if not raw_text.strip():
            self._set_state(State.IDLE)
            self._emit_error(
                "Could not transcribe audio. Try speaking more clearly.",
                "Empty transcript (provider=%s, model=%s, audio_s=%.2f)",
                self._stt_provider, self._stt_model, getattr(self, "_last_duration", 0.0),
            )
            return

        if self._mode == _MODE_ASSISTANT:
            self._run_assistant(raw_text)
            return

        text, proc_config = self._build_processing_config(raw_text)
        cfg = self._settings.config
        any_feature = proc_config.remove_fillers or proc_config.fix_grammar or proc_config.translation_target or proc_config.tone

        self._set_state(State.PROCESSING)

        # STT cost based on provider
        audio_s = getattr(self, "_last_duration", 0.0)
        if cfg.stt_provider == "groq":
            stt_cost = GroqClient.estimate_cost(audio_s, 0)
        elif cfg.stt_provider == "local":
            stt_cost = 0.0
        else:
            stt_cost = GeminiClient.estimate_cost(audio_s, len(raw_text))

        if not any_feature:
            self._on_ai_done(raw_text=raw_text, final_text=text, cost=stt_cost)
            return

        provider = self._resolve_text_provider()
        if provider is None:
            # Never drop what the user already said — paste it raw and say why it
            # skipped the cleanup (local Whisper needs no key, post-processing does).
            self._emit_error(
                "Pasted without AI cleanup — no API key for text processing. "
                "Add one in Settings → API Keys.",
                "No AI provider key for post-processing (configured=%s)", cfg.ai_model_provider,
            )
            self._on_ai_done(raw_text=raw_text, final_text=text, cost=stt_cost)
            return
        if provider == "claude":
            client = self._make_claude()
        elif provider == "groq":
            client = self._make_groq()
        else:
            client = self._make_gemini()

        self._ai_provider = provider
        self._ai_model = getattr(client, "ai_model", None) or getattr(client, "model", None)
        self._run_ctx = {
            "step": "ai_cleanup", "provider": provider, "model": self._ai_model,
            "audio_s": audio_s, "chars": len(text),
        }

        def _process():
            result = client.process_text(text, proc_config)
            if isinstance(client, GeminiClient):
                ai_cost = GeminiClient.estimate_cost(0, len(result))
            elif isinstance(client, GroqClient):
                # Llama 3.3 70B: $0.59/M input + $0.79/M output tokens
                ai_cost = (len(text) / 4 * 0.59 + len(result) / 4 * 0.79) / 1_000_000
            else:
                ai_cost = ClaudeClient.estimate_cost(len(text) // 4, len(result) // 4)
            return result, raw_text, stt_cost + ai_cost

        worker = _Worker(
            _process,
            on_result=lambda r: self._on_ai_done(raw_text=r[1], final_text=r[0], cost=r[2]),
            on_error=self._on_error,
        )
        self._pool.start(worker)

    def _run_assistant(self, command: str):
        cfg = self._settings.config
        context = self._assistant_context
        system_prompt = cfg.assistant_prompt

        self._set_state(State.PROCESSING)

        audio_s = getattr(self, "_last_duration", 0.0)
        if cfg.stt_provider == "groq":
            stt_cost = GroqClient.estimate_cost(audio_s, 0)
        elif cfg.stt_provider == "local":
            stt_cost = 0.0
        else:
            stt_cost = GeminiClient.estimate_cost(audio_s, len(command))

        provider_keys = {
            "claude": cfg.claude_api_key,
            "groq": cfg.groq_api_key,
            "gemini": cfg.gemini_api_key,
        }
        if cfg.assistant_model_provider:
            provider = cfg.assistant_model_provider
            if not provider_keys.get(provider):
                self._set_state(State.IDLE)
                self._emit_error(
                    f"No API key for {provider.capitalize()}. Add it in Settings → API Keys, "
                    "or pick a provider you have a key for in Settings → AI Assistant.",
                    "No API key for configured assistant provider %s", provider,
                )
                return
        elif provider_keys.get(cfg.ai_model_provider):
            provider = cfg.ai_model_provider
        else:
            provider = next((p for p in _PROVIDER_FALLBACK_ORDER if provider_keys.get(p)), None)
            if provider is None:
                self._set_state(State.IDLE)
                self._emit_error(
                    "No API key configured. Add one in Settings → API Keys.",
                    "No API key configured for assistant (fallback exhausted)",
                )
                return

        if provider == "claude":
            client = self._make_claude(for_assistant=True)
        elif provider == "groq":
            client = self._make_groq(for_assistant=True)
        else:
            client = self._make_gemini(for_assistant=True)

        in_chars = len(command) + (len(context) if context else 0)
        self._ai_provider = provider
        self._ai_model = getattr(client, "ai_model", None) or getattr(client, "model", None)
        self._run_ctx = {
            "step": "assistant", "provider": provider, "model": self._ai_model,
            "audio_s": audio_s, "chars": in_chars,
        }

        def _assist():
            result = client.run_assistant(command, context, system_prompt)
            if not result.strip():
                raise RuntimeError("Assistant returned an empty response.")
            if isinstance(client, GeminiClient):
                ai_cost = GeminiClient.estimate_cost(0, len(result))
            elif isinstance(client, GroqClient):
                ai_cost = (in_chars / 4 * 0.59 + len(result) / 4 * 0.79) / 1_000_000
            else:
                ai_cost = ClaudeClient.estimate_cost(in_chars // 4, len(result) // 4)
            return result, stt_cost + ai_cost

        worker = _Worker(
            _assist,
            on_result=lambda r: self._on_ai_done(raw_text=command, final_text=r[0], cost=r[1]),
            on_error=self._on_error,
        )
        self._pool.start(worker)

    def _on_ai_done(self, raw_text: str, final_text: str, cost: float):
        if self._cancel_flag:
            return
        # Called from worker thread — forward to main thread before touching Qt/clipboard
        self._inject_ready.emit(raw_text, final_text, cost)

    def _on_inject_ready(self, raw_text: str, final_text: str, cost: float):
        if self._cancel_flag:
            return
        # Runs in main thread — safe to use clipboard, QTimer, etc.
        self._set_state(State.INJECTING)
        self._injector.inject(final_text)
        self.transcription_ready.emit(final_text)
        self._set_state(State.IDLE)

        cfg = self._settings.config
        if self._mode == _MODE_ASSISTANT:
            ai_provider = cfg.assistant_model_provider or cfg.ai_model_provider
        else:
            ai_provider = cfg.ai_model_provider

        _log.info(
            "Dictation done (mode=%s, stt=%s/%s, ai=%s/%s, audio_s=%.2f, in_chars=%d, out_chars=%d, cost_usd=%.5f)",
            self._mode, self._stt_provider, self._stt_model, self._ai_provider, self._ai_model,
            getattr(self, "_last_duration", 0.0), len(raw_text), len(final_text), cost,
        )

        # DB insert in background so it doesn't block the main thread
        entry = TranscriptionEntry(
            raw_text=raw_text,
            final_text=final_text,
            duration_s=getattr(self, "_last_duration", 0.0),
            audio_s=getattr(self, "_last_duration", 0.0),
            char_count=len(final_text),
            ai_provider=ai_provider,
            cost_usd=cost,
        )

        def _save():
            self._db.insert(entry)
            self.history_updated.emit()

        self._pool.start(_Worker(_save))

    def _on_error(self, exc: Exception):
        ctx = self._run_ctx
        message = logger.redact(str(exc))
        # RuntimeError is how the API clients signal an already-readable error (bad
        # key, HTTP status, timeout); anything else is a bug worth a traceback.
        expected = isinstance(exc, RuntimeError)
        if self._cancel_flag:
            _log.info(
                "late error after cancel/timeout ignored (step=%s): %s: %s",
                ctx.get("step", "?"), type(exc).__name__, message,
            )
            return
        self._set_state(State.IDLE)
        _log.warning(
            "%s failed (provider=%s, model=%s, audio_s=%.2f, chars=%s): %s: %s",
            ctx.get("step", "?"), ctx.get("provider"), ctx.get("model"),
            ctx.get("audio_s") or 0.0, ctx.get("chars", "-"), type(exc).__name__, message,
            exc_info=None if expected else exc,
        )
        self.error_occurred.emit(f"Error: {message}")
