"""
Central pipeline orchestrator.
State machine: IDLE → RECORDING → TRANSCRIBING → PROCESSING → INJECTING → IDLE
"""

from __future__ import annotations

import re
import time
from enum import Enum, auto
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot

from voiceflow.api.claude_client import ClaudeClient
from voiceflow.api.gemini_client import GeminiClient
from voiceflow.config.schema import ProcessingConfig
from voiceflow.core.audio_recorder import AudioRecorder
from voiceflow.core.hotkey_manager import HotkeyManager
from voiceflow.core.text_injector import TextInjector
from voiceflow.storage.history_db import HistoryDB, TranscriptionEntry

if TYPE_CHECKING:
    from voiceflow.config.settings_manager import SettingsManager

_TRANSLATE_RE = re.compile(r"^translate\s+to\s+(\w+)[\s:,]+(.+)$", re.IGNORECASE | re.DOTALL)
_MIN_AUDIO_DURATION = 0.3  # seconds


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
                self._on_error(str(e))


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

        cfg = settings.config
        self._recorder = AudioRecorder(
            sample_rate=cfg.sample_rate,
            device_index=cfg.audio_device_index,
        )
        self._hotkey = HotkeyManager(cfg.hotkey)
        self._injector = TextInjector(hotkey_manager=self._hotkey)

        self._hotkey.hotkey_pressed.connect(self._on_hotkey_pressed)
        self._hotkey.hotkey_released.connect(self._on_hotkey_released)
        self._recorder.recording_finished.connect(self._on_recording_finished)
        self._inject_ready.connect(self._on_inject_ready)

        self._hotkey.start()

    # ── public API ──────────────────────────────────────────────────────────

    def reconfigure(self):
        cfg = self._settings.config
        self._hotkey.reconfigure(cfg.hotkey)
        self._recorder.sample_rate = cfg.sample_rate
        self._recorder.device_index = cfg.audio_device_index
        self._db.reconfigure(cfg.turso_db_url, cfg.turso_auth_token)

    def shutdown(self):
        self._hotkey.stop()
        if self._recorder.isRunning():
            self._recorder.stop_recording()
            self._recorder.wait(2000)

    @property
    def state(self) -> State:
        return self._state

    @property
    def recorder(self) -> AudioRecorder:
        return self._recorder

    # ── private helpers ──────────────────────────────────────────────────────

    def _set_state(self, state: State):
        self._state = state
        self.state_changed.emit(state)

    def _make_gemini(self) -> GeminiClient:
        cfg = self._settings.config
        return GeminiClient(cfg.gemini_api_key, cfg.stt_model, cfg.gemini_ai_model)

    def _make_claude(self) -> ClaudeClient:
        cfg = self._settings.config
        return ClaudeClient(cfg.claude_api_key, cfg.claude_ai_model)

    def _build_processing_config(self, raw_text: str) -> tuple[str, ProcessingConfig]:
        cfg = self._settings.config
        text = raw_text

        # Check for translation voice command
        translation_target = None
        m = _TRANSLATE_RE.match(raw_text.strip())
        if m:
            translation_target = m.group(1).strip().capitalize()
            text = m.group(2).strip()
        elif cfg.auto_translate:
            translation_target = cfg.translation_language

        proc = ProcessingConfig(
            remove_fillers=cfg.remove_fillers,
            fix_grammar=cfg.fix_grammar,
            translation_target=translation_target,
            tone=cfg.tone_adjustment_value if cfg.tone_adjustment_enabled else None,
        )
        return text, proc

    # ── slots ────────────────────────────────────────────────────────────────

    @pyqtSlot()
    def _on_hotkey_pressed(self):
        if self._state != State.IDLE:
            return
        self._set_state(State.RECORDING)
        self._recording_start = time.time()
        self._recorder.start_recording()

    @pyqtSlot()
    def _on_hotkey_released(self):
        if self._state != State.RECORDING:
            return
        self._set_state(State.TRANSCRIBING)
        self._recorder.stop_recording()

    @pyqtSlot(bytes)
    def _on_recording_finished(self, wav_bytes: bytes):
        duration = time.time() - self._recording_start
        if duration < _MIN_AUDIO_DURATION or not wav_bytes:
            self._set_state(State.IDLE)
            self.error_occurred.emit("Recording too short — hold the key and speak.")
            return

        self._last_wav = wav_bytes
        self._last_duration = duration

        cfg = self._settings.config
        _, proc_config = self._build_processing_config("")
        any_feature = bool(
            proc_config.remove_fillers or proc_config.fix_grammar
            or proc_config.translation_target or proc_config.tone
        )
        # Use a single combined call when Gemini handles both STT and post-processing
        use_combined = any_feature and not (cfg.ai_model_provider == "claude" and cfg.claude_api_key)

        gemini = self._make_gemini()
        audio_s = duration

        if use_combined:
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
            worker = _Worker(
                gemini.transcribe,
                wav_bytes,
                on_result=self._on_transcription_done,
                on_error=self._on_error,
            )
        self._pool.start(worker)

    def _on_transcription_done(self, raw_text: str):
        if not raw_text.strip():
            self._set_state(State.IDLE)
            self.error_occurred.emit("Could not transcribe audio. Try speaking more clearly.")
            return

        text, proc_config = self._build_processing_config(raw_text)
        cfg = self._settings.config
        any_feature = proc_config.remove_fillers or proc_config.fix_grammar or proc_config.translation_target or proc_config.tone

        self._set_state(State.PROCESSING)

        # STT cost is always incurred (Gemini transcription call)
        audio_s = getattr(self, "_last_duration", 0.0)
        stt_cost = GeminiClient.estimate_cost(audio_s, len(raw_text))

        if not any_feature:
            self._on_ai_done(raw_text=raw_text, final_text=text, cost=stt_cost)
            return

        if cfg.ai_model_provider == "claude" and cfg.claude_api_key:
            client = self._make_claude()
        else:
            client = self._make_gemini()

        def _process():
            result = client.process_text(text, proc_config)
            # AI processing cost: text tokens only, no audio
            if isinstance(client, GeminiClient):
                ai_cost = GeminiClient.estimate_cost(0, len(result))
            else:
                ai_cost = ClaudeClient.estimate_cost(len(text) // 4, len(result) // 4)
            return result, raw_text, stt_cost + ai_cost

        worker = _Worker(
            _process,
            on_result=lambda r: self._on_ai_done(raw_text=r[1], final_text=r[0], cost=r[2]),
            on_error=self._on_error,
        )
        self._pool.start(worker)

    def _on_ai_done(self, raw_text: str, final_text: str, cost: float):
        # Called from worker thread — forward to main thread before touching Qt/clipboard
        self._inject_ready.emit(raw_text, final_text, cost)

    def _on_inject_ready(self, raw_text: str, final_text: str, cost: float):
        # Runs in main thread — safe to use clipboard, QTimer, etc.
        self._set_state(State.INJECTING)
        self._injector.inject(final_text)
        self.transcription_ready.emit(final_text)
        self._set_state(State.IDLE)

        # DB insert in background so it doesn't block the main thread
        entry = TranscriptionEntry(
            raw_text=raw_text,
            final_text=final_text,
            duration_s=getattr(self, "_last_duration", 0.0),
            audio_s=getattr(self, "_last_duration", 0.0),
            char_count=len(final_text),
            ai_provider=self._settings.config.ai_model_provider,
            cost_usd=cost,
        )

        def _save():
            self._db.insert(entry)
            self.history_updated.emit()

        self._pool.start(_Worker(_save))

    def _on_error(self, message: str):
        self._set_state(State.IDLE)
        self.error_occurred.emit(f"Error: {message}")
