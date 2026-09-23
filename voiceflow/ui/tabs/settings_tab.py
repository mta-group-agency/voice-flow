from __future__ import annotations

import threading

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QScrollArea, QSlider, QTextEdit,
    QVBoxLayout, QWidget,
)

from voiceflow.api.claude_client import ClaudeClient
from voiceflow.api.gemini_client import GeminiClient
from voiceflow.api.groq_client import GroqClient
from voiceflow.api.local_whisper_client import LocalWhisperClient, MODEL_INFO
from voiceflow.config.schema import AppConfig
from voiceflow.core import autostart
from voiceflow.ui.widgets.hotkey_capture import HotkeyCaptureWidget
from voiceflow.ui.widgets.toggle_switch import ToggleSwitch


class SettingsTab(QWidget):
    theme_requested = pyqtSignal(str)
    settings_saved = pyqtSignal()

    def __init__(self, settings, pipeline, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._pipeline = pipeline
        # No empty-string sentinel for stt_provider/ai_model_provider (unlike
        # assistant_model_provider), so "user hasn't deliberately chosen yet" is
        # tracked with these — set only from real user interaction (QComboBox.activated /
        # QButtonGroup.buttonClicked), never from _load_values or the realign methods
        # themselves, or a fresh install could never auto-realign past its first click.
        self._stt_provider_user_touched = False
        self._ai_provider_user_touched = False
        # True for the duration of _load_values(): the key fields get populated one at a
        # time there (_gemini_key before _groq_key, _claude_key later still), so a realign
        # reacting mid-load would judge a provider "keyless" just because its field hasn't
        # been set yet this round. _load_values sets the resolved provider directly from
        # cfg instead (see its STT/AI processing sections) and this flag keeps the realign
        # methods from acting on that half-loaded, misleading snapshot in between.
        self._loading = False
        self._build_ui()
        self._load_values()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        inner = QWidget()
        scroll.setWidget(inner)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        layout = QVBoxLayout(inner)
        layout.setContentsMargins(28, 22, 28, 24)
        layout.setSpacing(16)

        self._build_hotkey_section(layout)
        self._build_api_keys_section(layout)
        self._build_stt_section(layout)
        self._build_ai_processing_section(layout)
        self._build_assistant_section(layout)
        self._build_turso_section(layout)
        self._build_system_section(layout)
        self._build_appearance_section(layout)
        self._build_save_row(layout)
        layout.addStretch()

        # Both provider-warning labels and all three key fields exist by now (API Keys
        # section is built first) — refresh on every keystroke so pasting a key clears
        # the warning immediately, without Save or a restart.
        # Realigns run first so a key that just appeared can move a radio/combo before
        # the warning below is computed for the (possibly now-stale) selection.
        self._gemini_key.textChanged.connect(self._maybe_realign_assistant_provider)
        self._groq_key.textChanged.connect(self._maybe_realign_assistant_provider)
        self._claude_key.textChanged.connect(self._maybe_realign_assistant_provider)
        self._gemini_key.textChanged.connect(self._maybe_realign_stt_provider)
        self._groq_key.textChanged.connect(self._maybe_realign_stt_provider)
        self._gemini_key.textChanged.connect(self._maybe_realign_ai_provider)
        self._groq_key.textChanged.connect(self._maybe_realign_ai_provider)
        self._claude_key.textChanged.connect(self._maybe_realign_ai_provider)
        self._gemini_key.textChanged.connect(self._refresh_provider_warnings)
        self._groq_key.textChanged.connect(self._refresh_provider_warnings)
        self._claude_key.textChanged.connect(self._refresh_provider_warnings)

        # Combo → config field, so a model-list refresh can read the value that
        # should survive the repopulation from the config (not the widget's own
        # possibly-stale current text — see _repopulate_combo).
        self._model_fields: dict[QComboBox, str] = {
            self._stt_model: "stt_model",
            self._groq_stt_model: "groq_stt_model",
            self._gemini_ai_model: "gemini_ai_model",
            self._claude_ai_model: "claude_ai_model",
            self._groq_ai_model: "groq_ai_model",
            self._assistant_gemini_model: "assistant_gemini_model",
            self._assistant_claude_model: "assistant_claude_model",
            self._assistant_groq_model: "assistant_groq_model",
        }

    # ── Section builders ──────────────────────────────────────────────────────

    def _build_hotkey_section(self, layout: QVBoxLayout):
        group = QGroupBox("Push-to-Talk Hotkey")
        form = QFormLayout(group)
        self._hotkey_widget = HotkeyCaptureWidget()
        self._hotkey_widget.setObjectName("primary")
        self._hotkey_widget.key_captured.connect(self._on_hotkey_captured)
        hint = QLabel("Click, press your key combo (e.g. Right Alt), then release to confirm.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        form.addRow("Record Key:", self._hotkey_widget)
        form.addRow("", hint)

        self._hotkey_assistant_widget = HotkeyCaptureWidget()
        self._hotkey_assistant_widget.setObjectName("primary")
        self._hotkey_assistant_widget.key_captured.connect(self._on_hotkey_captured)
        assistant_hint = QLabel(
            "Second key — records a command for the AI assistant (e.g. Right Ctrl). "
            "The assistant runs it and pastes the result."
        )
        assistant_hint.setObjectName("hint")
        assistant_hint.setWordWrap(True)
        form.addRow("Assistant Key:", self._hotkey_assistant_widget)
        form.addRow("", assistant_hint)
        layout.addWidget(group)

    def _build_api_keys_section(self, layout: QVBoxLayout):
        group = QGroupBox("API Keys")
        vbox = QVBoxLayout(group)
        vbox.setSpacing(10)

        hint = QLabel(
            "Leave a key empty if you do not use that provider. Groq alone covers "
            "speech-to-text, text processing and the assistant."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        vbox.addWidget(hint)

        form = QFormLayout()
        form.setContentsMargins(0, 4, 0, 0)

        self._gemini_key = QLineEdit()
        self._gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._gemini_key.setPlaceholderText("AIza…")
        form.addRow("Gemini API Key:", self._key_row(self._gemini_key, self._test_gemini))

        self._groq_key = QLineEdit()
        self._groq_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._groq_key.setPlaceholderText("gsk_…")
        form.addRow("Groq API Key:", self._key_row(self._groq_key, self._test_groq))

        self._claude_key = QLineEdit()
        self._claude_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._claude_key.setPlaceholderText("sk-ant-…")
        form.addRow("Claude API Key:", self._key_row(self._claude_key, self._test_claude))

        vbox.addLayout(form)
        layout.addWidget(group)

    def _build_stt_section(self, layout: QVBoxLayout):
        group = QGroupBox("Speech-to-Text")
        vbox = QVBoxLayout(group)
        vbox.setSpacing(10)

        # Provider selector
        row = QHBoxLayout()
        row.addWidget(QLabel("Provider:"))
        self._stt_provider_combo = QComboBox()
        self._stt_provider_combo.addItem("Gemini (default)", "gemini")
        self._stt_provider_combo.addItem("Groq — Whisper (~10× faster)", "groq")
        self._stt_provider_combo.addItem("Local — faster-whisper (NVIDIA GPU)", "local")
        self._stt_provider_combo.setFixedWidth(290)
        row.addWidget(self._stt_provider_combo)
        row.addStretch()
        vbox.addLayout(row)

        self._stt_info_lbl = QLabel()
        self._stt_info_lbl.setObjectName("hint")
        self._stt_info_lbl.setWordWrap(True)
        vbox.addWidget(self._stt_info_lbl)

        # Gemini sub-section (model only — API key lives in the API Keys section above)
        self._stt_gemini_widget = QWidget()
        f = QFormLayout(self._stt_gemini_widget)
        f.setContentsMargins(0, 0, 0, 0)
        self._stt_model = QComboBox()
        self._stt_model.setEditable(False)
        self._stt_model.addItems(["gemini-2.5-flash", "gemini-2.5-flash-lite"])
        f.addRow("Model:", self._stt_model)
        vbox.addWidget(self._stt_gemini_widget)

        # Groq sub-section (model only — API key lives in the API Keys section above)
        self._stt_groq_widget = QWidget()
        f = QFormLayout(self._stt_groq_widget)
        f.setContentsMargins(0, 0, 0, 0)
        self._groq_stt_model = QComboBox()
        self._groq_stt_model.setEditable(False)
        self._groq_stt_model.addItems(["whisper-large-v3-turbo", "whisper-large-v3"])
        f.addRow("Model:", self._groq_stt_model)
        vbox.addWidget(self._stt_groq_widget)

        # Local sub-section (model picker + download)
        self._stt_local_widget = QWidget()
        local_vbox = QVBoxLayout(self._stt_local_widget)
        local_vbox.setContentsMargins(0, 0, 0, 0)
        local_vbox.setSpacing(8)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model size:"))
        self._local_model_combo = QComboBox()
        for name, info in MODEL_INFO.items():
            self._local_model_combo.addItem(
                f"{name}  ({info['size_mb']} MB · {info['speed']})", name
            )
        self._local_model_combo.setFixedWidth(310)
        model_row.addWidget(self._local_model_combo)
        model_row.addStretch()
        local_vbox.addLayout(model_row)

        dl_row = QHBoxLayout()
        self._download_btn = QPushButton("Download / load model")
        self._download_btn.setObjectName("primary")
        self._download_btn.setFixedWidth(190)
        self._download_btn.clicked.connect(self._start_model_download)
        self._download_status = QLabel("")
        self._download_status.setObjectName("hint")
        self._download_status.setWordWrap(True)
        dl_row.addWidget(self._download_btn)
        dl_row.addWidget(self._download_status)
        dl_row.addStretch()
        local_vbox.addLayout(dl_row)

        folder_row = QHBoxLayout()
        open_folder_btn = QPushButton("Open models folder")
        open_folder_btn.setObjectName("ghost")
        open_folder_btn.setFixedWidth(160)
        open_folder_btn.clicked.connect(self._open_models_folder)
        self._disk_usage_lbl = QLabel()
        self._disk_usage_lbl.setObjectName("hint")
        folder_row.addWidget(open_folder_btn)
        folder_row.addWidget(self._disk_usage_lbl)
        folder_row.addStretch()
        local_vbox.addLayout(folder_row)
        self._refresh_disk_usage()

        vbox.addWidget(self._stt_local_widget)
        layout.addWidget(group)

        self._stt_provider_combo.currentIndexChanged.connect(self._on_stt_provider_changed)
        # activated (not currentIndexChanged) fires only on real user interaction —
        # not on the programmatic setCurrentIndex in _load_values or in the realign
        # method below, which is exactly the "did the user deliberately choose" signal.
        self._stt_provider_combo.activated.connect(self._on_stt_provider_touched)

    def _build_ai_processing_section(self, layout: QVBoxLayout):
        group = QGroupBox("AI Text Processing")
        vbox = QVBoxLayout(group)
        vbox.setSpacing(10)

        # Master toggle
        toggle_row = QHBoxLayout()
        lbl = QLabel("Process transcriptions with AI")
        lbl.setFixedWidth(250)
        self._ai_processing_toggle = ToggleSwitch()
        toggle_row.addWidget(lbl)
        toggle_row.addWidget(self._ai_processing_toggle)
        toggle_row.addStretch()
        vbox.addLayout(toggle_row)

        toggle_hint = QLabel(
            "Cleans up dictated text (fillers, grammar, translation, tone). "
            "Leave off for raw transcription."
        )
        toggle_hint.setObjectName("hint")
        toggle_hint.setWordWrap(True)
        vbox.addWidget(toggle_hint)

        # Collapsible body — everything specific to dictation post-processing,
        # including the provider choice (the Assistant below has its own).
        self._ai_processing_body = QWidget()
        body_vbox = QVBoxLayout(self._ai_processing_body)
        body_vbox.setContentsMargins(0, 4, 0, 0)
        body_vbox.setSpacing(10)

        provider_row = QHBoxLayout()
        provider_row.addWidget(QLabel("Provider:"))
        self._radio_gemini = QRadioButton("Gemini")
        self._radio_claude = QRadioButton("Claude")
        self._radio_groq_ai = QRadioButton("Groq")
        self._ai_provider_group = QButtonGroup(self)
        for btn in (self._radio_gemini, self._radio_claude, self._radio_groq_ai):
            self._ai_provider_group.addButton(btn)
        provider_row.addWidget(self._radio_gemini)
        provider_row.addWidget(self._radio_claude)
        provider_row.addWidget(self._radio_groq_ai)
        provider_row.addStretch()
        body_vbox.addLayout(provider_row)

        self._ai_provider_warning = QLabel()
        self._ai_provider_warning.setObjectName("model_stale_warning")
        self._ai_provider_warning.setWordWrap(True)
        self._ai_provider_warning.setVisible(False)
        body_vbox.addWidget(self._ai_provider_warning)

        # Contextual model panels (API keys live in the API Keys section above)
        self._ai_gemini_widget = QWidget()
        fg = QFormLayout(self._ai_gemini_widget)
        fg.setContentsMargins(0, 0, 0, 0)
        self._gemini_ai_model = QComboBox()
        self._gemini_ai_model.setEditable(False)
        self._gemini_ai_model.addItems(["gemini-2.5-flash", "gemini-2.5-flash-lite"])
        fg.addRow("Gemini model:", self._gemini_ai_model)
        body_vbox.addWidget(self._ai_gemini_widget)

        self._ai_claude_widget = QWidget()
        fc = QFormLayout(self._ai_claude_widget)
        fc.setContentsMargins(0, 0, 0, 0)
        self._claude_ai_model = QComboBox()
        self._claude_ai_model.setEditable(False)
        self._claude_ai_model.addItems(["claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5-20251001"])
        fc.addRow("Claude model:", self._claude_ai_model)
        body_vbox.addWidget(self._ai_claude_widget)

        self._ai_groq_widget = QWidget()
        fgr = QFormLayout(self._ai_groq_widget)
        fgr.setContentsMargins(0, 0, 0, 0)
        self._groq_ai_model = QComboBox()
        self._groq_ai_model.setEditable(False)
        self._groq_ai_model.addItems([
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
        ])
        fgr.addRow("Groq model:", self._groq_ai_model)
        body_vbox.addWidget(self._ai_groq_widget)

        # Custom prompt
        prompt_lbl = QLabel("Custom prompt (leave empty to use the feature toggles below):")
        prompt_lbl.setObjectName("hint")
        prompt_lbl.setWordWrap(True)
        body_vbox.addWidget(prompt_lbl)

        self._ai_custom_prompt = QTextEdit()
        self._ai_custom_prompt.setFixedHeight(72)
        self._ai_custom_prompt.setPlaceholderText(
            "e.g. Remove filler words. Fix grammar. Keep the original language."
        )
        body_vbox.addWidget(self._ai_custom_prompt)

        # Features — what the processing above actually toggles on the text.
        self._toggle_fillers = self._feature_row(body_vbox, "Remove Filler Words")
        self._toggle_grammar = self._feature_row(body_vbox, "Fix Grammar & Punctuation")

        intensity_row = QHBoxLayout()
        intensity_lbl = QLabel("AI Intensity")
        intensity_lbl.setFixedWidth(200)
        self._intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self._intensity_slider.setMinimum(1)
        self._intensity_slider.setMaximum(5)
        self._intensity_slider.setValue(3)
        self._intensity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._intensity_slider.setTickInterval(1)
        self._intensity_slider.setFixedWidth(130)
        self._intensity_value_lbl = QLabel("3 — Balanced")
        self._intensity_value_lbl.setObjectName("hint")
        self._intensity_slider.valueChanged.connect(self._on_intensity_changed)
        intensity_row.addWidget(intensity_lbl)
        intensity_row.addWidget(self._intensity_slider)
        intensity_row.addSpacing(10)
        intensity_row.addWidget(self._intensity_value_lbl)
        intensity_row.addStretch()
        body_vbox.addLayout(intensity_row)

        tr_row = QHBoxLayout()
        tr_lbl = QLabel("Auto-Translate")
        tr_lbl.setFixedWidth(200)
        self._toggle_translate = ToggleSwitch()
        self._translate_lang = QComboBox()
        self._translate_lang.addItems(["English", "Polish", "German", "French", "Spanish", "Italian"])
        self._translate_lang.setFixedWidth(130)
        tr_row.addWidget(tr_lbl)
        tr_row.addWidget(self._toggle_translate)
        tr_row.addSpacing(12)
        tr_row.addWidget(QLabel("→"))
        tr_row.addWidget(self._translate_lang)
        tr_row.addStretch()
        body_vbox.addLayout(tr_row)

        tone_row = QHBoxLayout()
        tone_lbl = QLabel("Tone Adjustment")
        tone_lbl.setFixedWidth(200)
        self._toggle_tone = ToggleSwitch()
        self._tone_value = QComboBox()
        self._tone_value.addItems(["Formal", "Casual", "Professional", "Friendly"])
        self._tone_value.setFixedWidth(130)
        tone_row.addWidget(tone_lbl)
        tone_row.addWidget(self._toggle_tone)
        tone_row.addSpacing(12)
        tone_row.addWidget(QLabel("→"))
        tone_row.addWidget(self._tone_value)
        tone_row.addStretch()
        body_vbox.addLayout(tone_row)

        latency_note = QLabel(
            "Note: AI processing adds ~0.5–2s latency depending on the provider."
        )
        latency_note.setObjectName("hint")
        latency_note.setWordWrap(True)
        body_vbox.addWidget(latency_note)

        vbox.addWidget(self._ai_processing_body)
        layout.addWidget(group)

        self._ai_processing_toggle.toggled.connect(
            lambda on: self._ai_processing_body.setVisible(on)
        )
        self._radio_gemini.toggled.connect(self._update_ai_provider_widgets)
        self._radio_claude.toggled.connect(self._update_ai_provider_widgets)
        self._radio_groq_ai.toggled.connect(self._update_ai_provider_widgets)
        # buttonClicked (not toggled) fires only on a real user click — not on the
        # programmatic setChecked in _load_values or in the realign method below.
        self._ai_provider_group.buttonClicked.connect(self._on_ai_provider_touched)
        self._toggle_translate.toggled.connect(lambda on: self._translate_lang.setEnabled(on))
        self._toggle_tone.toggled.connect(lambda on: self._tone_value.setEnabled(on))

    def _build_assistant_section(self, layout: QVBoxLayout):
        group = QGroupBox("AI Assistant")
        vbox = QVBoxLayout(group)
        vbox.setSpacing(10)

        intro = QLabel(
            "A second hotkey records a command that the assistant runs and pastes as a "
            "ready result (e.g. \"write a thank-you email\"). It works even when AI Text "
            "Processing above is off."
        )
        intro.setObjectName("hint")
        intro.setWordWrap(True)
        vbox.addWidget(intro)

        # Own provider choice — independent from AI Text Processing above, so it
        # needs its own QButtonGroup (otherwise Qt would treat all six radios as
        # one mutually-exclusive set).
        provider_row = QHBoxLayout()
        provider_row.addWidget(QLabel("Provider:"))
        self._radio_assistant_gemini = QRadioButton("Gemini")
        self._radio_assistant_claude = QRadioButton("Claude")
        self._radio_assistant_groq = QRadioButton("Groq")
        self._assistant_provider_group = QButtonGroup(self)
        for btn in (self._radio_assistant_gemini, self._radio_assistant_claude, self._radio_assistant_groq):
            self._assistant_provider_group.addButton(btn)
        provider_row.addWidget(self._radio_assistant_gemini)
        provider_row.addWidget(self._radio_assistant_claude)
        provider_row.addWidget(self._radio_assistant_groq)
        provider_row.addStretch()
        vbox.addLayout(provider_row)

        self._assistant_provider_warning = QLabel()
        self._assistant_provider_warning.setObjectName("model_stale_warning")
        self._assistant_provider_warning.setWordWrap(True)
        self._assistant_provider_warning.setVisible(False)
        vbox.addWidget(self._assistant_provider_warning)

        self._assistant_gemini_widget = QWidget()
        fag = QFormLayout(self._assistant_gemini_widget)
        fag.setContentsMargins(0, 0, 0, 0)
        self._assistant_gemini_model = QComboBox()
        self._assistant_gemini_model.setEditable(False)
        self._assistant_gemini_model.addItems(["gemini-2.5-flash", "gemini-2.5-flash-lite"])
        fag.addRow("Gemini model:", self._assistant_gemini_model)
        vbox.addWidget(self._assistant_gemini_widget)

        self._assistant_claude_widget = QWidget()
        fac = QFormLayout(self._assistant_claude_widget)
        fac.setContentsMargins(0, 0, 0, 0)
        self._assistant_claude_model = QComboBox()
        self._assistant_claude_model.setEditable(False)
        self._assistant_claude_model.addItems(["claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5-20251001"])
        fac.addRow("Claude model:", self._assistant_claude_model)
        vbox.addWidget(self._assistant_claude_widget)

        self._assistant_groq_widget = QWidget()
        fagr = QFormLayout(self._assistant_groq_widget)
        fagr.setContentsMargins(0, 0, 0, 0)
        self._assistant_groq_model = QComboBox()
        self._assistant_groq_model.setEditable(False)
        self._assistant_groq_model.addItems([
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
        ])
        fagr.addRow("Groq model:", self._assistant_groq_model)
        vbox.addWidget(self._assistant_groq_widget)

        prompt_lbl = QLabel("Assistant system prompt:")
        prompt_lbl.setObjectName("hint")
        prompt_lbl.setWordWrap(True)
        vbox.addWidget(prompt_lbl)

        self._assistant_prompt = QTextEdit()
        self._assistant_prompt.setFixedHeight(110)
        vbox.addWidget(self._assistant_prompt)

        clip_row = QHBoxLayout()
        clip_lbl = QLabel("Use clipboard as context")
        clip_lbl.setFixedWidth(250)
        self._assistant_clipboard_toggle = ToggleSwitch()
        clip_row.addWidget(clip_lbl)
        clip_row.addWidget(self._assistant_clipboard_toggle)
        clip_row.addStretch()
        vbox.addLayout(clip_row)

        clip_hint = QLabel(
            "When enabled, the clipboard contents at the moment you press the assistant "
            "hotkey are attached as context to your command."
        )
        clip_hint.setObjectName("hint")
        clip_hint.setWordWrap(True)
        vbox.addWidget(clip_hint)

        layout.addWidget(group)

        self._radio_assistant_gemini.toggled.connect(self._update_assistant_provider_widgets)
        self._radio_assistant_claude.toggled.connect(self._update_assistant_provider_widgets)
        self._radio_assistant_groq.toggled.connect(self._update_assistant_provider_widgets)

    def _build_turso_section(self, layout: QVBoxLayout):
        group = QGroupBox("History Storage")
        vbox = QVBoxLayout(group)
        vbox.setSpacing(10)

        toggle_row = QHBoxLayout()
        lbl = QLabel("Store transcriptions in Turso cloud database")
        lbl.setFixedWidth(330)
        self._turso_toggle = ToggleSwitch()
        toggle_row.addWidget(lbl)
        toggle_row.addWidget(self._turso_toggle)
        toggle_row.addStretch()
        vbox.addLayout(toggle_row)

        self._turso_fields = QWidget()
        f = QFormLayout(self._turso_fields)
        f.setContentsMargins(0, 0, 0, 0)
        self._turso_url = QLineEdit()
        self._turso_url.setPlaceholderText("libsql://mydb-org.turso.io")
        f.addRow("Turso DB URL:", self._turso_url)
        self._turso_token = QLineEdit()
        self._turso_token.setEchoMode(QLineEdit.EchoMode.Password)
        self._turso_token.setPlaceholderText("auth token…")
        f.addRow("Auth Token:", self._key_row(self._turso_token, self._test_turso))
        vbox.addWidget(self._turso_fields)

        layout.addWidget(group)
        self._turso_toggle.toggled.connect(
            lambda on: self._turso_fields.setVisible(on)
        )

    def _build_system_section(self, layout: QVBoxLayout):
        group = QGroupBox("System")
        vbox = QVBoxLayout(group)
        row = QHBoxLayout()
        lbl = QLabel("Start with Windows")
        lbl.setFixedWidth(200)
        self._toggle_autostart = ToggleSwitch()
        self._toggle_autostart.toggled.connect(self._on_autostart_toggled)
        row.addWidget(lbl)
        row.addWidget(self._toggle_autostart)
        row.addStretch()
        if not autostart.is_frozen():
            note = QLabel("(available only in the compiled .exe)")
            note.setObjectName("hint")
            row.addWidget(note)
            self._toggle_autostart.setEnabled(False)
        vbox.addLayout(row)
        layout.addWidget(group)

    def _build_appearance_section(self, layout: QVBoxLayout):
        group = QGroupBox("Appearance")
        vbox = QVBoxLayout(group)
        row = QHBoxLayout()
        row.setSpacing(8)
        lbl = QLabel("Theme:")
        lbl.setFixedWidth(60)
        row.addWidget(lbl)
        self._theme_buttons: dict[str, QPushButton] = {}
        for key, label in (("dark", "🌙 Dark"), ("light", "☀ Light"), ("system", "System")):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, k=key: self.theme_requested.emit(k))
            self._theme_buttons[key] = btn
            row.addWidget(btn)
        row.addStretch()
        vbox.addLayout(row)
        layout.addWidget(group)
        self.update_theme_buttons("dark")

    def _build_save_row(self, layout: QVBoxLayout):
        row = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("primary")
        save_btn.setFixedWidth(160)
        save_btn.clicked.connect(self._save)
        row.addWidget(save_btn)
        self._saved_lbl = QLabel("Settings saved")
        self._saved_lbl.setObjectName("hint")
        self._saved_lbl.setVisible(False)
        row.addWidget(self._saved_lbl)
        row.addStretch()
        layout.addLayout(row)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(lambda: self._saved_lbl.setVisible(False))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _key_row(self, field: QLineEdit, test_fn) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(field)
        btn = QPushButton("Test")
        btn.setObjectName("ghost")
        btn.setFixedWidth(60)
        btn.clicked.connect(test_fn)
        row.addWidget(btn)
        return w

    def _feature_row(self, parent_layout: QVBoxLayout, label: str) -> ToggleSwitch:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(200)
        toggle = ToggleSwitch()
        row.addWidget(lbl)
        row.addWidget(toggle)
        row.addStretch()
        parent_layout.addLayout(row)
        return toggle

    _INTENSITY_LABELS = {
        1: "1 — Minimum (preserve speaking style)",
        2: "2 — Light corrections",
        3: "3 — Balanced",
        4: "4 — Thorough cleanup",
        5: "5 — Aggressive polish",
    }

    _STT_INFO = {
        "gemini": "~3–8s  ·  ~$0.003 / 1 000 chars",
        "groq":   "~0.2s  ·  ~$0.001 / 1 000 chars  (groq.com — free tier available)",
        "local":  (
            "~0.15–0.8s  ·  free  ·  no internet required\n"
            "NVIDIA GPU recommended for fast inference (CPU fallback: 2–5s)."
        ),
    }

    # ── Event handlers ────────────────────────────────────────────────────────

    def _open_models_folder(self):
        from voiceflow.api.local_whisper_client import MODELS_DIR
        import os
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(str(MODELS_DIR))

    def _refresh_disk_usage(self):
        from voiceflow.api.local_whisper_client import MODELS_DIR
        parts = []
        for name in MODEL_INFO:
            model_dir = MODELS_DIR / f"models--Systran--faster-whisper-{name}"
            if model_dir.exists():
                size_bytes = sum(f.stat().st_size for f in model_dir.rglob("*") if f.is_file())
                parts.append(f"{name}: {size_bytes / (1024**3):.2f} GB")
        self._disk_usage_lbl.setText(
            "Downloaded: " + "  ·  ".join(parts) if parts else "No models downloaded yet."
        )

    def _on_stt_provider_changed(self, _index=None):
        provider = self._stt_provider_combo.currentData()
        self._stt_gemini_widget.setVisible(provider == "gemini")
        self._stt_groq_widget.setVisible(provider == "groq")
        self._stt_local_widget.setVisible(provider == "local")
        self._stt_info_lbl.setText(self._STT_INFO.get(provider, ""))
        if provider == "local":
            model = self._local_model_combo.currentData()
            if LocalWhisperClient.is_loaded(model):
                self._download_status.setText("Model loaded ✓")

    def _update_ai_provider_widgets(self):
        self._ai_gemini_widget.setVisible(self._radio_gemini.isChecked())
        self._ai_claude_widget.setVisible(self._radio_claude.isChecked())
        self._ai_groq_widget.setVisible(self._radio_groq_ai.isChecked())
        self._refresh_provider_warnings()

    def _update_assistant_provider_widgets(self):
        self._assistant_gemini_widget.setVisible(self._radio_assistant_gemini.isChecked())
        self._assistant_claude_widget.setVisible(self._radio_assistant_claude.isChecked())
        self._assistant_groq_widget.setVisible(self._radio_assistant_groq.isChecked())
        self._refresh_provider_warnings()

    _PROVIDER_LABELS = {"gemini": "Gemini", "claude": "Claude", "groq": "Groq"}
    # Preference order for auto-realign when nothing has been deliberately chosen yet —
    # groq first, since the free tier is this project's default track. Shared by the
    # Assistant and AI Text Processing realigns/initial load.
    _PROVIDER_ORDER = ("groq", "gemini", "claude")
    # Same idea for Speech-to-Text, which only groq and gemini support in this app.
    _STT_PROVIDER_ORDER = ("groq", "gemini")

    def _current_ai_provider(self) -> str:
        if self._radio_claude.isChecked():
            return "claude"
        if self._radio_groq_ai.isChecked():
            return "groq"
        return "gemini"

    def _current_assistant_provider(self) -> str:
        if self._radio_assistant_claude.isChecked():
            return "claude"
        if self._radio_assistant_groq.isChecked():
            return "groq"
        return "gemini"

    def _missing_key_warning(self, provider: str) -> str:
        field = {"gemini": self._gemini_key, "claude": self._claude_key, "groq": self._groq_key}.get(provider)
        if field is None or field.text().strip():
            return ""
        label = self._PROVIDER_LABELS.get(provider, provider.capitalize())
        return f"No {label} API key yet — add one in the API Keys section above."

    def _refresh_provider_warnings(self):
        # A fresh install with no key typed anywhere yet doesn't need a red warning —
        # the API Keys section right above is already the obvious next step.
        any_key = bool(
            self._gemini_key.text().strip()
            or self._groq_key.text().strip()
            or self._claude_key.text().strip()
        )
        text = self._missing_key_warning(self._current_ai_provider()) if any_key else ""
        self._ai_provider_warning.setText(text)
        self._ai_provider_warning.setVisible(bool(text))
        text = self._missing_key_warning(self._current_assistant_provider()) if any_key else ""
        self._assistant_provider_warning.setText(text)
        self._assistant_provider_warning.setVisible(bool(text))

    def _on_stt_provider_touched(self, _index=None):
        self._stt_provider_user_touched = True

    def _on_ai_provider_touched(self, _button=None):
        self._ai_provider_user_touched = True

    def _key_field_cleared(self) -> bool:
        """Realigning is for "a key appeared", not "a key vanished" — otherwise clearing
        a field to paste a new key silently moves the provider somewhere else and the
        refilled key no longer brings it back."""
        sender = self.sender()
        return isinstance(sender, QLineEdit) and not sender.text().strip()

    def _maybe_realign_stt_provider(self):
        """Same idea as _maybe_realign_assistant_provider, for the Speech-to-Text
        provider combo. stt_provider has no "" (inherit) sentinel — it always holds a
        real value, even a fresh install's untouched schema default — so "not yet
        deliberately chosen" is tracked with _stt_provider_user_touched instead, set
        only by the combo's own `activated` (real user interaction, never _load_values
        or the setCurrentIndex below). "local" needs no key and is left alone."""
        if self._loading or self._stt_provider_user_touched or self._key_field_cleared():
            return
        current = self._stt_provider_combo.currentData()
        if current == "local":
            return
        keys = {"groq": self._groq_key.text().strip(), "gemini": self._gemini_key.text().strip()}
        if keys.get(current):
            return
        target = next((p for p in self._STT_PROVIDER_ORDER if keys[p]), None)
        if not target:
            return
        idx = self._stt_provider_combo.findData(target)
        if idx < 0:
            return
        self._stt_provider_combo.blockSignals(True)
        self._stt_provider_combo.setCurrentIndex(idx)
        self._stt_provider_combo.blockSignals(False)
        self._on_stt_provider_changed()

    def _maybe_realign_ai_provider(self):
        """Same idea as _maybe_realign_assistant_provider, for the AI Text Processing
        provider radios. ai_model_provider has no "" (inherit) sentinel either, so
        this is guarded by _ai_provider_user_touched instead, set only by the button
        group's own buttonClicked (real user click, never _load_values or the
        setChecked below)."""
        if self._loading or self._ai_provider_user_touched or self._key_field_cleared():
            return
        keys = {
            "groq": self._groq_key.text().strip(),
            "gemini": self._gemini_key.text().strip(),
            "claude": self._claude_key.text().strip(),
        }
        if keys[self._current_ai_provider()]:
            return
        target = next((p for p in self._PROVIDER_ORDER if keys[p]), None)
        if not target:
            return
        radios = (self._radio_gemini, self._radio_claude, self._radio_groq_ai)
        target_radio = {
            "gemini": self._radio_gemini,
            "claude": self._radio_claude,
            "groq": self._radio_groq_ai,
        }[target]
        for r in radios:
            r.blockSignals(True)
        target_radio.setChecked(True)
        for r in radios:
            r.blockSignals(False)
        self._update_ai_provider_widgets()

    def _maybe_realign_assistant_provider(self):
        """Wired to the key fields' textChanged only — never to the radio buttons — so
        this reacts purely to a key appearing and a deliberate radio click always sticks.
        Never touches an explicit saved choice (config.assistant_model_provider)."""
        if (self._loading or self._settings.config.assistant_model_provider
                or self._key_field_cleared()):
            return
        keys = {
            "groq": self._groq_key.text().strip(),
            "gemini": self._gemini_key.text().strip(),
            "claude": self._claude_key.text().strip(),
        }
        if keys[self._current_assistant_provider()]:
            return
        target = next((p for p in self._PROVIDER_ORDER if keys[p]), None)
        if not target:
            return
        radios = (self._radio_assistant_gemini, self._radio_assistant_claude, self._radio_assistant_groq)
        target_radio = {
            "gemini": self._radio_assistant_gemini,
            "claude": self._radio_assistant_claude,
            "groq": self._radio_assistant_groq,
        }[target]
        for r in radios:
            r.blockSignals(True)
        target_radio.setChecked(True)
        for r in radios:
            r.blockSignals(False)
        self._update_assistant_provider_widgets()

    def apply_discovered_models(self, provider: str, payload, healed: dict[str, str] | None = None):
        if provider == "gemini":
            for combo in (self._stt_model, self._gemini_ai_model, self._assistant_gemini_model):
                self._repopulate_combo(combo, payload, healed)
        elif provider == "claude":
            for combo in (self._claude_ai_model, self._assistant_claude_model):
                self._repopulate_combo(combo, payload, healed)
        elif provider == "groq":
            self._repopulate_combo(self._groq_stt_model, payload["stt"], healed)
            for combo in (self._groq_ai_model, self._assistant_groq_model):
                self._repopulate_combo(combo, payload["chat"], healed)

    def _repopulate_combo(
        self, combo: QComboBox, fresh_items: list[str], healed: dict[str, str] | None = None
    ):
        if not fresh_items:
            return
        field = self._model_fields.get(combo)
        current = combo.currentText()
        # An unsaved pick the provider still offers wins; otherwise fall back to the
        # config, which is where auto-healing writes a replacement for a dead model.
        if current in fresh_items or not field:
            saved = current
        else:
            saved = getattr(self._settings.config, field)
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(fresh_items)
        idx = combo.findText(saved)
        if idx >= 0:
            combo.setCurrentIndex(idx)
            healed_from = (healed or {}).get(field) if field else None
            if healed_from:
                self._set_model_status(
                    combo,
                    warn_text=f'Auto-switched: "{healed_from}" is no longer offered by the provider.',
                )
            else:
                self._set_model_status(combo, ok_text="Model list updated from the provider's API.")
        else:
            combo.insertItem(0, saved)
            combo.setCurrentIndex(0)
            self._set_model_status(
                combo, warn_text=f'"{saved}" is not on the provider\'s current model list.'
            )
        combo.blockSignals(False)

    def _set_model_status(self, combo: QComboBox, ok_text: str | None = None, warn_text: str | None = None):
        ok_label = getattr(combo, "_fresh_label", None)
        if ok_label is None:
            ok_label = QLabel()
            ok_label.setObjectName("hint")
            ok_label.setWordWrap(True)
            ok_label.setVisible(False)
            warn_label = QLabel()
            warn_label.setObjectName("model_stale_warning")
            warn_label.setWordWrap(True)
            warn_label.setVisible(False)
            parent_layout = combo.parentWidget().layout()
            if isinstance(parent_layout, QFormLayout):
                parent_layout.addRow("", ok_label)
                parent_layout.addRow("", warn_label)
            else:
                parent_layout.addWidget(ok_label)
                parent_layout.addWidget(warn_label)
            combo._fresh_label = ok_label
            combo._stale_warning_label = warn_label
        else:
            warn_label = combo._stale_warning_label

        ok_label.setText(ok_text or "")
        ok_label.setVisible(bool(ok_text))
        warn_label.setText(warn_text or "")
        warn_label.setVisible(bool(warn_text))

    def _on_intensity_changed(self, value: int):
        self._intensity_value_lbl.setText(self._INTENSITY_LABELS.get(value, str(value)))

    def _on_hotkey_captured(self, key: str):
        pass

    def _on_autostart_toggled(self, enabled: bool):
        ok = autostart.set_enabled(enabled)
        if not ok:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Autostart", "Could not update Windows registry.")
            self._toggle_autostart.setChecked(autostart.is_enabled())

    def _start_model_download(self):
        import queue
        from voiceflow.api.local_whisper_client import MODELS_DIR
        model = self._local_model_combo.currentData()
        expected_mb = MODEL_INFO.get(model, {}).get("disk_mb", 0)

        self._download_btn.setEnabled(False)
        self._download_status.setText("Starting…")

        model_dir = MODELS_DIR / f"models--Systran--faster-whisper-{model}"

        # Thread-safe queue: worker puts status strings, timer reads on main thread
        status_q: queue.SimpleQueue[str] = queue.SimpleQueue()

        self._dl_progress_timer = QTimer(self)
        self._dl_progress_timer.setInterval(500)

        _in_loading_phase = [False]

        def _update_progress():
            # Drain all pending status messages first
            while not status_q.empty():
                s = status_q.get()
                if s == "downloading":
                    self._download_status.setText("Downloading / verifying files…")
                elif s == "loading":
                    _in_loading_phase[0] = True
                    self._download_status.setText(
                        "Loading model into GPU… (first run may take up to 30s)"
                    )
                elif s.startswith("done:"):
                    self._dl_progress_timer.stop()
                    self._on_download_done(True)
                    return
                elif s.startswith("error:"):
                    self._dl_progress_timer.stop()
                    self._on_download_done(False, s[6:])
                    return

            # Show download progress only while downloading
            if _in_loading_phase[0]:
                return
            try:
                total_bytes = sum(
                    f.stat().st_size for f in model_dir.rglob("*") if f.is_file()
                ) if model_dir.exists() else 0
                mb = total_bytes / (1024 * 1024)
                if expected_mb > 0 and mb > 0:
                    pct = min(99, int(mb / expected_mb * 100))
                    self._download_status.setText(
                        f"Downloading… {mb:.0f} MB / {expected_mb} MB ({pct}%)"
                    )
                elif mb > 0:
                    self._download_status.setText(f"Downloading… {mb:.0f} MB")
            except Exception:
                pass

        self._dl_progress_timer.timeout.connect(_update_progress)
        self._dl_progress_timer.start()

        def _on_status(status: str):
            # Called from worker thread — only put into queue, never touch Qt objects
            status_q.put(status)

        def _run():
            try:
                LocalWhisperClient.preload_model(model, on_status=_on_status)
                status_q.put("done:")
            except Exception as e:
                status_q.put(f"error:{str(e)[:120]}")

        threading.Thread(target=_run, daemon=True).start()

    def _on_download_done(self, success: bool, error: str = ""):
        if hasattr(self, "_dl_progress_timer"):
            self._dl_progress_timer.stop()
        self._download_btn.setEnabled(True)
        if success:
            self._download_status.setText("Model ready ✓  No restart needed — active immediately.")
        else:
            self._download_status.setText(f"Error: {error[:80]}")
        self._refresh_disk_usage()

    def update_theme_buttons(self, active: str):
        for key, btn in self._theme_buttons.items():
            btn.setObjectName("theme_active" if key == active else "theme_inactive")
            btn.style().polish(btn)

    # ── Load / Save ───────────────────────────────────────────────────────────

    def _select_model(self, combo: QComboBox, value: str):
        """Non-editable combos silently ignore setCurrentText for values outside the list,
        so a model healed from the live API would fall back to item 0 and be re-saved."""
        if not value:
            return
        idx = combo.findText(value)
        if idx < 0:
            combo.insertItem(0, value)
            idx = 0
        combo.setCurrentIndex(idx)

    def _load_values(self):
        self._loading = True
        try:
            self._load_values_impl()
        finally:
            self._loading = False

    def _load_values_impl(self):
        cfg = self._settings.config

        # Hotkey
        self._hotkey_widget.set_key(cfg.hotkey)
        self._hotkey_assistant_widget.set_key(cfg.hotkey_assistant)

        # Assistant
        self._assistant_prompt.setPlainText(cfg.assistant_prompt)
        self._assistant_clipboard_toggle.setChecked(cfg.assistant_use_clipboard)
        self._select_model(self._assistant_gemini_model, cfg.assistant_gemini_model)
        self._select_model(self._assistant_claude_model, cfg.assistant_claude_model)
        self._select_model(self._assistant_groq_model, cfg.assistant_groq_model)

        # Same resolution order as Pipeline._run_assistant: explicit choice wins; else the
        # inherited (dictation) provider if it has a key; else the first provider that has
        # a key at all (groq first — the free tier is this project's default track); else
        # leave it as ai_model_provider, same as before.
        provider_keys = {
            "groq": cfg.groq_api_key,
            "gemini": cfg.gemini_api_key,
            "claude": cfg.claude_api_key,
        }
        if cfg.assistant_model_provider:
            assistant_provider = cfg.assistant_model_provider
        elif provider_keys.get(cfg.ai_model_provider):
            assistant_provider = cfg.ai_model_provider
        else:
            assistant_provider = next(
                (p for p in ("groq", "gemini", "claude") if provider_keys.get(p)),
                cfg.ai_model_provider,
            )
        if assistant_provider == "claude":
            self._radio_assistant_claude.setChecked(True)
        elif assistant_provider == "groq":
            self._radio_assistant_groq.setChecked(True)
        else:
            self._radio_assistant_gemini.setChecked(True)
        self._update_assistant_provider_widgets()

        # STT
        # Same idea as the assistant resolution above, 2-way (Claude has no STT here):
        # configured provider if it has a key, else the first of groq/gemini that does;
        # else leave it as stt_provider. Computed directly from cfg (not the realign
        # method, which _loading blocks right now) so the initial pick doesn't depend on
        # the order the key fields below happen to populate in.
        stt_keys = {"groq": cfg.groq_api_key, "gemini": cfg.gemini_api_key}
        if cfg.stt_provider == "local" or stt_keys.get(cfg.stt_provider):
            stt_provider = cfg.stt_provider
        else:
            stt_provider = next((p for p in self._STT_PROVIDER_ORDER if stt_keys.get(p)), cfg.stt_provider)
        idx = self._stt_provider_combo.findData(stt_provider)
        self._stt_provider_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._select_model(self._stt_model, cfg.stt_model)
        self._gemini_key.setText(cfg.gemini_api_key)
        self._select_model(self._groq_stt_model, cfg.groq_stt_model)
        self._groq_key.setText(cfg.groq_api_key)
        for i in range(self._local_model_combo.count()):
            if self._local_model_combo.itemData(i) == cfg.local_whisper_model:
                self._local_model_combo.setCurrentIndex(i)
                break
        self._on_stt_provider_changed()

        # Turso
        self._turso_toggle.setChecked(cfg.turso_enabled)
        self._turso_fields.setVisible(cfg.turso_enabled)
        self._turso_url.setText(cfg.turso_db_url)
        self._turso_token.setText(cfg.turso_auth_token)

        # AI processing
        self._ai_processing_toggle.setChecked(cfg.ai_processing_enabled)
        self._ai_processing_body.setVisible(cfg.ai_processing_enabled)
        self._ai_custom_prompt.setPlainText(cfg.ai_custom_prompt)

        # Same cascade as STT above, full three-way groq/gemini/claude — computed
        # directly from cfg for the same reason: correctness must not depend on the
        # order _gemini_key/_groq_key/_claude_key happen to populate in below.
        ai_keys = {"groq": cfg.groq_api_key, "gemini": cfg.gemini_api_key, "claude": cfg.claude_api_key}
        if ai_keys.get(cfg.ai_model_provider):
            ai_provider = cfg.ai_model_provider
        else:
            ai_provider = next((p for p in self._PROVIDER_ORDER if ai_keys.get(p)), cfg.ai_model_provider)
        if ai_provider == "claude":
            self._radio_claude.setChecked(True)
        elif ai_provider == "groq":
            self._radio_groq_ai.setChecked(True)
        else:
            self._radio_gemini.setChecked(True)

        self._select_model(self._gemini_ai_model, cfg.gemini_ai_model)
        self._select_model(self._claude_ai_model, cfg.claude_ai_model)
        self._claude_key.setText(cfg.claude_api_key)
        self._select_model(self._groq_ai_model, cfg.groq_ai_model)
        self._update_ai_provider_widgets()

        # Features
        self._toggle_fillers.setChecked(cfg.remove_fillers)
        self._toggle_grammar.setChecked(cfg.fix_grammar)
        self._intensity_slider.setValue(cfg.ai_intensity)
        self._on_intensity_changed(cfg.ai_intensity)
        self._toggle_translate.setChecked(cfg.auto_translate)
        self._translate_lang.setEnabled(cfg.auto_translate)
        idx = self._translate_lang.findText(cfg.translation_language)
        if idx >= 0:
            self._translate_lang.setCurrentIndex(idx)
        self._toggle_tone.setChecked(cfg.tone_adjustment_enabled)
        self._tone_value.setEnabled(cfg.tone_adjustment_enabled)
        idx = self._tone_value.findText(cfg.tone_adjustment_value.capitalize())
        if idx >= 0:
            self._tone_value.setCurrentIndex(idx)

        # System
        self._toggle_autostart.setChecked(autostart.is_enabled())

    def _save(self):
        s = self._settings

        # Hotkey
        s.set("hotkey", self._hotkey_widget.current_key())
        s.set("hotkey_assistant", self._hotkey_assistant_widget.current_key())

        # Assistant
        assistant_prompt = self._assistant_prompt.toPlainText().strip()
        s.set("assistant_prompt", assistant_prompt or AppConfig.assistant_prompt)
        s.set("assistant_use_clipboard", self._assistant_clipboard_toggle.isChecked())
        s.set("assistant_gemini_model", self._assistant_gemini_model.currentText())
        s.set("assistant_claude_model", self._assistant_claude_model.currentText())
        s.set("assistant_groq_model", self._assistant_groq_model.currentText())

        if self._radio_assistant_claude.isChecked():
            assistant_provider = "claude"
        elif self._radio_assistant_groq.isChecked():
            assistant_provider = "groq"
        else:
            assistant_provider = "gemini"
        provider_keys = {
            "groq": self._groq_key.text().strip(),
            "gemini": self._gemini_key.text().strip(),
            "claude": self._claude_key.text().strip(),
        }
        if not provider_keys[assistant_provider]:
            # Selected provider has no key (whether or not another one does) — persist ""
            # (inherit) rather than lock in a choice we already know would hard-error at
            # runtime, and rather than freeze out _maybe_realign_assistant_provider the
            # instant a key is pasted later (its guard is "assistant_model_provider is
            # already explicit", which a saved real provider name would trip forever).
            assistant_provider = ""
        s.set("assistant_model_provider", assistant_provider)

        # STT
        s.set("stt_provider",        self._stt_provider_combo.currentData())
        s.set("stt_model",           self._stt_model.currentText())
        s.set("gemini_api_key",      self._gemini_key.text().strip())
        s.set("groq_stt_model",      self._groq_stt_model.currentText())
        s.set("groq_api_key",        self._groq_key.text().strip())
        s.set("local_whisper_model", self._local_model_combo.currentData() or "small")

        # Turso
        s.set("turso_enabled",    self._turso_toggle.isChecked())
        s.set("turso_db_url",     self._turso_url.text().strip())
        s.set("turso_auth_token", self._turso_token.text().strip())

        # AI processing
        s.set("ai_processing_enabled", self._ai_processing_toggle.isChecked())
        s.set("ai_custom_prompt",      self._ai_custom_prompt.toPlainText().strip())

        if self._radio_claude.isChecked():
            ai_provider = "claude"
        elif self._radio_groq_ai.isChecked():
            ai_provider = "groq"
        else:
            ai_provider = "gemini"
        s.set("ai_model_provider", ai_provider)
        s.set("gemini_ai_model",   self._gemini_ai_model.currentText())
        s.set("claude_ai_model",   self._claude_ai_model.currentText())
        s.set("claude_api_key",    self._claude_key.text().strip())
        s.set("groq_ai_model",     self._groq_ai_model.currentText())

        # Features
        s.set("remove_fillers",         self._toggle_fillers.isChecked())
        s.set("fix_grammar",            self._toggle_grammar.isChecked())
        s.set("ai_intensity",           self._intensity_slider.value())
        s.set("auto_translate",         self._toggle_translate.isChecked())
        s.set("translation_language",   self._translate_lang.currentText())
        s.set("tone_adjustment_enabled", self._toggle_tone.isChecked())
        s.set("tone_adjustment_value",   self._tone_value.currentText().lower())

        self._pipeline.reconfigure()
        self.settings_saved.emit()
        self._saved_lbl.setVisible(True)
        self._save_timer.start(3000)

    # ── API connection tests ──────────────────────────────────────────────────

    def _test_gemini(self):
        from PyQt6.QtWidgets import QMessageBox
        ok = GeminiClient(
            self._gemini_key.text().strip(),
            self._stt_model.currentText(),
            self._gemini_ai_model.currentText(),
        ).test_connection()
        QMessageBox.information(self, "Gemini", "Connection successful!") if ok else \
        QMessageBox.warning(self, "Gemini", "Connection failed. Check your API key.")

    def _test_claude(self):
        from PyQt6.QtWidgets import QMessageBox
        ok = ClaudeClient(
            self._claude_key.text().strip(),
            self._claude_ai_model.currentText(),
        ).test_connection()
        QMessageBox.information(self, "Claude", "Connection successful!") if ok else \
        QMessageBox.warning(self, "Claude", "Connection failed. Check your API key.")

    def _test_groq(self):
        from PyQt6.QtWidgets import QMessageBox
        ok = GroqClient(
            self._groq_key.text().strip(),
            self._groq_stt_model.currentText(),
            self._groq_ai_model.currentText(),
        ).test_connection()
        QMessageBox.information(self, "Groq", "Connection successful!") if ok else \
        QMessageBox.warning(self, "Groq", "Connection failed. Check your API key.")

    def _test_turso(self):
        from PyQt6.QtWidgets import QMessageBox
        from voiceflow.storage.history_db import HistoryDB
        db = HistoryDB(self._turso_url.text().strip(), self._turso_token.text().strip())
        if db.is_enabled:
            QMessageBox.information(self, "Turso", "Schema initialized successfully!")
        else:
            QMessageBox.warning(self, "Turso", "Could not connect. Check URL and token.")
