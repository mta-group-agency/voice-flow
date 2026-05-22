from __future__ import annotations

import threading

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QScrollArea, QSlider, QTextEdit,
    QVBoxLayout, QWidget,
)

from voiceflow.api.claude_client import ClaudeClient
from voiceflow.api.gemini_client import GeminiClient
from voiceflow.api.groq_client import GroqClient
from voiceflow.api.local_whisper_client import LocalWhisperClient, MODEL_INFO
from voiceflow.core import autostart
from voiceflow.ui.widgets.hotkey_capture import HotkeyCaptureWidget
from voiceflow.ui.widgets.toggle_switch import ToggleSwitch


class SettingsTab(QWidget):
    theme_requested = pyqtSignal(str)

    def __init__(self, settings, pipeline, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._pipeline = pipeline
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
        self._build_stt_section(layout)
        self._build_turso_section(layout)
        self._build_ai_processing_section(layout)
        self._build_features_section(layout)
        self._build_system_section(layout)
        self._build_appearance_section(layout)
        self._build_save_row(layout)
        layout.addStretch()

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

        # Gemini sub-section (model + API key)
        self._stt_gemini_widget = QWidget()
        f = QFormLayout(self._stt_gemini_widget)
        f.setContentsMargins(0, 0, 0, 0)
        self._stt_model = QComboBox()
        self._stt_model.setEditable(True)
        self._stt_model.addItems(["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"])
        f.addRow("Model:", self._stt_model)
        self._gemini_key = QLineEdit()
        self._gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._gemini_key.setPlaceholderText("AIza…")
        f.addRow("Gemini API Key:", self._key_row(self._gemini_key, self._test_gemini))
        vbox.addWidget(self._stt_gemini_widget)

        # Groq sub-section (model + API key)
        self._stt_groq_widget = QWidget()
        f = QFormLayout(self._stt_groq_widget)
        f.setContentsMargins(0, 0, 0, 0)
        self._groq_stt_model = QComboBox()
        self._groq_stt_model.setEditable(True)
        self._groq_stt_model.addItems(["whisper-large-v3-turbo", "whisper-large-v3"])
        f.addRow("Model:", self._groq_stt_model)
        self._groq_key = QLineEdit()
        self._groq_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._groq_key.setPlaceholderText("gsk_…")
        f.addRow("Groq API Key:", self._key_row(self._groq_key, self._test_groq))
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

        vbox.addWidget(self._stt_local_widget)
        layout.addWidget(group)

        self._stt_provider_combo.currentIndexChanged.connect(self._on_stt_provider_changed)

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

        # Collapsible body
        self._ai_processing_body = QWidget()
        body_vbox = QVBoxLayout(self._ai_processing_body)
        body_vbox.setContentsMargins(0, 4, 0, 0)
        body_vbox.setSpacing(10)

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

        latency_note = QLabel(
            "Note: AI processing adds ~0.5–2s latency depending on the provider."
        )
        latency_note.setObjectName("hint")
        latency_note.setWordWrap(True)
        body_vbox.addWidget(latency_note)

        # AI provider
        provider_row = QHBoxLayout()
        provider_row.addWidget(QLabel("Provider:"))
        self._radio_gemini = QRadioButton("Gemini")
        self._radio_claude = QRadioButton("Claude")
        self._radio_groq_ai = QRadioButton("Groq")
        provider_row.addWidget(self._radio_gemini)
        provider_row.addWidget(self._radio_claude)
        provider_row.addWidget(self._radio_groq_ai)
        provider_row.addStretch()
        body_vbox.addLayout(provider_row)

        # Contextual API key / model panels
        self._ai_gemini_widget = QWidget()
        fg = QFormLayout(self._ai_gemini_widget)
        fg.setContentsMargins(0, 0, 0, 0)
        self._gemini_ai_model = QComboBox()
        self._gemini_ai_model.setEditable(True)
        self._gemini_ai_model.addItems(["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"])
        fg.addRow("Gemini model:", self._gemini_ai_model)
        # Gemini key is shared with STT — show a note pointing to STT section
        key_note = QLabel("API key is set in the Speech-to-Text section above.")
        key_note.setObjectName("hint")
        fg.addRow("", key_note)
        body_vbox.addWidget(self._ai_gemini_widget)

        self._ai_claude_widget = QWidget()
        fc = QFormLayout(self._ai_claude_widget)
        fc.setContentsMargins(0, 0, 0, 0)
        self._claude_ai_model = QComboBox()
        self._claude_ai_model.setEditable(True)
        self._claude_ai_model.addItems(["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5-20251001"])
        fc.addRow("Claude model:", self._claude_ai_model)
        self._claude_key = QLineEdit()
        self._claude_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._claude_key.setPlaceholderText("sk-ant-…")
        fc.addRow("Claude API Key:", self._key_row(self._claude_key, self._test_claude))
        body_vbox.addWidget(self._ai_claude_widget)

        self._ai_groq_widget = QWidget()
        fgr = QFormLayout(self._ai_groq_widget)
        fgr.setContentsMargins(0, 0, 0, 0)
        self._groq_ai_model = QComboBox()
        self._groq_ai_model.setEditable(True)
        self._groq_ai_model.addItems([
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
        ])
        fgr.addRow("Groq model:", self._groq_ai_model)
        groq_key_note = QLabel("API key is set in the Speech-to-Text section above.")
        groq_key_note.setObjectName("hint")
        fgr.addRow("", groq_key_note)
        body_vbox.addWidget(self._ai_groq_widget)

        vbox.addWidget(self._ai_processing_body)
        layout.addWidget(group)

        self._ai_processing_toggle.toggled.connect(
            lambda on: self._ai_processing_body.setVisible(on)
        )
        self._radio_gemini.toggled.connect(self._update_ai_provider_widgets)
        self._radio_claude.toggled.connect(self._update_ai_provider_widgets)
        self._radio_groq_ai.toggled.connect(self._update_ai_provider_widgets)

    def _build_features_section(self, layout: QVBoxLayout):
        group = QGroupBox("Features")
        vbox = QVBoxLayout(group)
        vbox.setSpacing(12)

        self._toggle_fillers = self._feature_row(vbox, "Remove Filler Words")
        self._toggle_grammar = self._feature_row(vbox, "Fix Grammar & Punctuation")

        # AI Intensity slider
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
        vbox.addLayout(intensity_row)

        # Auto-translate
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
        vbox.addLayout(tr_row)

        # Tone adjustment
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
        vbox.addLayout(tone_row)

        layout.addWidget(group)

        self._toggle_translate.toggled.connect(lambda on: self._translate_lang.setEnabled(on))
        self._toggle_tone.toggled.connect(lambda on: self._tone_value.setEnabled(on))

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
        gemini = self._radio_gemini.isChecked()
        claude = self._radio_claude.isChecked()
        groq = self._radio_groq_ai.isChecked()
        self._ai_gemini_widget.setVisible(gemini)
        self._ai_claude_widget.setVisible(claude)
        self._ai_groq_widget.setVisible(groq)

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
        from voiceflow.api.local_whisper_client import MODELS_DIR
        model = self._local_model_combo.currentData()
        # disk_mb accounts for HF cache storing blobs + snapshots (~2x model size on Windows)
        expected_mb = MODEL_INFO.get(model, {}).get("disk_mb", 0)

        self._download_btn.setEnabled(False)
        self._download_status.setText("Starting…")

        self._dl_progress_timer = QTimer(self)
        self._dl_progress_timer.setInterval(1000)

        def _update_progress():
            try:
                total_bytes = sum(
                    f.stat().st_size for f in MODELS_DIR.rglob("*") if f.is_file()
                )
                mb = total_bytes / (1024 * 1024)
                if expected_mb > 0:
                    pct = min(99, int(mb / expected_mb * 100))
                    self._download_status.setText(
                        f"Downloading… {mb:.0f} MB / {expected_mb} MB ({pct}%)"
                    )
                else:
                    self._download_status.setText(f"Downloading… {mb:.0f} MB")
            except Exception:
                pass

        self._dl_progress_timer.timeout.connect(_update_progress)
        self._dl_progress_timer.start()

        def _on_status(status: str):
            if status == "loading":
                QTimer.singleShot(0, self._dl_progress_timer.stop)
                QTimer.singleShot(0, lambda: self._download_status.setText(
                    "Loading model into GPU… (may take up to 60s on first run)"
                ))

        def _run():
            try:
                LocalWhisperClient.preload_model(model, on_status=_on_status)
                QTimer.singleShot(0, lambda: self._on_download_done(True))
            except Exception as e:
                err = str(e)
                QTimer.singleShot(0, lambda: self._on_download_done(False, err))

        threading.Thread(target=_run, daemon=True).start()

    def _on_download_done(self, success: bool, error: str = ""):
        if hasattr(self, "_dl_progress_timer"):
            self._dl_progress_timer.stop()
        self._download_btn.setEnabled(True)
        if success:
            self._download_status.setText("Model ready ✓  No restart needed — active immediately.")
        else:
            self._download_status.setText(f"Error: {error[:80]}")

    def update_theme_buttons(self, active: str):
        for key, btn in self._theme_buttons.items():
            btn.setObjectName("theme_active" if key == active else "theme_inactive")
            btn.style().polish(btn)

    # ── Load / Save ───────────────────────────────────────────────────────────

    def _load_values(self):
        cfg = self._settings.config

        # Hotkey
        self._hotkey_widget.set_key(cfg.hotkey)

        # STT
        idx = self._stt_provider_combo.findData(cfg.stt_provider)
        self._stt_provider_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._stt_model.setCurrentText(cfg.stt_model)
        self._gemini_key.setText(cfg.gemini_api_key)
        self._groq_stt_model.setCurrentText(cfg.groq_stt_model)
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

        if cfg.ai_model_provider == "claude":
            self._radio_claude.setChecked(True)
        elif cfg.ai_model_provider == "groq":
            self._radio_groq_ai.setChecked(True)
        else:
            self._radio_gemini.setChecked(True)

        self._gemini_ai_model.setCurrentText(cfg.gemini_ai_model)
        self._claude_ai_model.setCurrentText(cfg.claude_ai_model)
        self._claude_key.setText(cfg.claude_api_key)
        self._groq_ai_model.setCurrentText(cfg.groq_ai_model)
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
