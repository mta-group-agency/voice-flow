from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from voiceflow.api.claude_client import ClaudeClient
from voiceflow.api.gemini_client import GeminiClient
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

        # ── API Keys ──────────────────────────────────────────────────────────
        api_group = QGroupBox("API Keys")
        api_form = QFormLayout(api_group)
        api_form.setSpacing(10)
        api_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._gemini_key = QLineEdit()
        self._gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._gemini_key.setPlaceholderText("AIza…")
        api_form.addRow("Gemini API Key:", self._key_row(self._gemini_key, self._test_gemini))

        self._claude_key = QLineEdit()
        self._claude_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._claude_key.setPlaceholderText("sk-ant-…")
        api_form.addRow("Claude API Key:", self._key_row(self._claude_key, self._test_claude))

        self._turso_url = QLineEdit()
        self._turso_url.setPlaceholderText("libsql://mydb-org.turso.io")
        api_form.addRow("Turso DB URL:", self._turso_url)

        self._turso_token = QLineEdit()
        self._turso_token.setEchoMode(QLineEdit.EchoMode.Password)
        self._turso_token.setPlaceholderText("auth token…")
        api_form.addRow("Turso Auth Token:", self._key_row(self._turso_token, self._test_turso))

        layout.addWidget(api_group)

        # ── Hotkey ────────────────────────────────────────────────────────────
        hotkey_group = QGroupBox("Push-to-Talk Hotkey")
        hotkey_layout = QFormLayout(hotkey_group)
        self._hotkey_widget = HotkeyCaptureWidget()
        self._hotkey_widget.setObjectName("hotkey_btn")
        self._hotkey_widget.key_captured.connect(self._on_hotkey_captured)
        hint = QLabel("Click, press your key combo (e.g. Ctrl+Win), then release to confirm.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        hotkey_layout.addRow("Record Key:", self._hotkey_widget)
        hotkey_layout.addRow("", hint)
        layout.addWidget(hotkey_group)

        # ── AI Model ──────────────────────────────────────────────────────────
        model_group = QGroupBox("AI Text Processing")
        model_layout = QVBoxLayout(model_group)
        model_layout.setSpacing(10)

        provider_row = QHBoxLayout()
        from PyQt6.QtWidgets import QRadioButton
        self._radio_gemini = QRadioButton("Gemini")
        self._radio_claude = QRadioButton("Claude")
        provider_row.addWidget(QLabel("Provider:"))
        provider_row.addWidget(self._radio_gemini)
        provider_row.addWidget(self._radio_claude)
        provider_row.addStretch()
        model_layout.addLayout(provider_row)

        gemini_form = QFormLayout()
        self._gemini_model = QComboBox()
        self._gemini_model.setEditable(True)
        self._gemini_model.addItems(["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"])
        gemini_form.addRow("Gemini model:", self._gemini_model)
        model_layout.addLayout(gemini_form)

        claude_form = QFormLayout()
        self._claude_model = QComboBox()
        self._claude_model.setEditable(True)
        self._claude_model.addItems(["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5-20251001"])
        claude_form.addRow("Claude model:", self._claude_model)
        model_layout.addLayout(claude_form)

        stt_form = QFormLayout()
        self._stt_model = QComboBox()
        self._stt_model.setEditable(True)
        self._stt_model.addItems(["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"])
        stt_hint = QLabel("Used for audio → text transcription.")
        stt_hint.setObjectName("hint")
        stt_form.addRow("STT model:", self._stt_model)
        stt_form.addRow("", stt_hint)
        model_layout.addLayout(stt_form)

        layout.addWidget(model_group)

        # ── Features ──────────────────────────────────────────────────────────
        feat_group = QGroupBox("Features")
        feat_layout = QVBoxLayout(feat_group)
        feat_layout.setSpacing(12)

        self._toggle_fillers = self._feature_row(feat_layout, "Remove Filler Words")
        self._toggle_grammar = self._feature_row(feat_layout, "Fix Grammar & Punctuation")

        tr_row = QHBoxLayout()
        tr_label = QLabel("Auto-Translate")
        tr_label.setFixedWidth(200)
        self._toggle_translate = ToggleSwitch()
        self._translate_lang = QComboBox()
        self._translate_lang.addItems(["English", "Polish", "German", "French", "Spanish", "Italian"])
        self._translate_lang.setFixedWidth(130)
        tr_row.addWidget(tr_label)
        tr_row.addWidget(self._toggle_translate)
        tr_row.addSpacing(12)
        tr_row.addWidget(QLabel("→"))
        tr_row.addWidget(self._translate_lang)
        tr_row.addStretch()
        feat_layout.addLayout(tr_row)

        tone_row = QHBoxLayout()
        tone_label = QLabel("Tone Adjustment")
        tone_label.setFixedWidth(200)
        self._toggle_tone = ToggleSwitch()
        self._tone_value = QComboBox()
        self._tone_value.addItems(["Formal", "Casual", "Professional", "Friendly"])
        self._tone_value.setFixedWidth(130)
        tone_row.addWidget(tone_label)
        tone_row.addWidget(self._toggle_tone)
        tone_row.addSpacing(12)
        tone_row.addWidget(QLabel("→"))
        tone_row.addWidget(self._tone_value)
        tone_row.addStretch()
        feat_layout.addLayout(tone_row)

        layout.addWidget(feat_group)

        # ── System ────────────────────────────────────────────────────────────
        sys_group = QGroupBox("System")
        sys_layout = QVBoxLayout(sys_group)
        autostart_row = QHBoxLayout()
        autostart_lbl = QLabel("Start with Windows")
        autostart_lbl.setFixedWidth(200)
        self._toggle_autostart = ToggleSwitch()
        self._toggle_autostart.toggled.connect(self._on_autostart_toggled)
        autostart_row.addWidget(autostart_lbl)
        autostart_row.addWidget(self._toggle_autostart)
        autostart_row.addStretch()
        if not autostart.is_frozen():
            note = QLabel("(available only in the compiled .exe)")
            note.setObjectName("hint")
            autostart_row.addWidget(note)
            self._toggle_autostart.setEnabled(False)
        sys_layout.addLayout(autostart_row)
        layout.addWidget(sys_group)

        # ── Appearance ────────────────────────────────────────────────────────
        appear_group = QGroupBox("Appearance")
        appear_layout = QVBoxLayout(appear_group)
        theme_row = QHBoxLayout()
        theme_row.setSpacing(8)
        theme_lbl = QLabel("Theme:")
        theme_lbl.setFixedWidth(60)
        theme_row.addWidget(theme_lbl)

        self._theme_buttons: dict[str, QPushButton] = {}
        for key, label in (("dark", "🌙 Dark"), ("light", "☀ Light"), ("system", "System")):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, k=key: self.theme_requested.emit(k))
            self._theme_buttons[key] = btn
            theme_row.addWidget(btn)
        theme_row.addStretch()
        appear_layout.addLayout(theme_row)
        layout.addWidget(appear_group)

        self.update_theme_buttons("dark")

        # ── Save ──────────────────────────────────────────────────────────────
        save_row = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("primary")
        save_btn.setFixedWidth(160)
        save_btn.clicked.connect(self._save)
        save_row.addWidget(save_btn)

        self._saved_lbl = QLabel("Settings saved")
        self._saved_lbl.setObjectName("hint")
        self._saved_lbl.setVisible(False)
        save_row.addWidget(self._saved_lbl)
        save_row.addStretch()
        layout.addLayout(save_row)
        layout.addStretch()

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(lambda: self._saved_lbl.setVisible(False))

        # Connect toggles to enabled state
        self._toggle_translate.toggled.connect(lambda on: self._translate_lang.setEnabled(on))
        self._toggle_tone.toggled.connect(lambda on: self._tone_value.setEnabled(on))
        self._radio_gemini.toggled.connect(self._update_model_visibility)
        self._radio_claude.toggled.connect(self._update_model_visibility)

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

    def _update_model_visibility(self):
        gemini = self._radio_gemini.isChecked()
        self._gemini_model.setEnabled(gemini)
        self._claude_model.setEnabled(not gemini)

    def update_theme_buttons(self, active: str):
        for key, btn in self._theme_buttons.items():
            btn.setObjectName("theme_active" if key == active else "theme_inactive")
            btn.style().polish(btn)

    # ── Load / Save ───────────────────────────────────────────────────────────

    def _load_values(self):
        cfg = self._settings.config
        self._gemini_key.setText(cfg.gemini_api_key)
        self._claude_key.setText(cfg.claude_api_key)
        self._turso_url.setText(cfg.turso_db_url)
        self._turso_token.setText(cfg.turso_auth_token)
        self._hotkey_widget.set_key(cfg.hotkey)

        if cfg.ai_model_provider == "claude":
            self._radio_claude.setChecked(True)
        else:
            self._radio_gemini.setChecked(True)

        self._gemini_model.setCurrentText(cfg.gemini_ai_model)
        self._claude_model.setCurrentText(cfg.claude_ai_model)
        self._stt_model.setCurrentText(cfg.stt_model)
        self._toggle_fillers.setChecked(cfg.remove_fillers)
        self._toggle_grammar.setChecked(cfg.fix_grammar)
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
        self._update_model_visibility()
        self._toggle_autostart.setChecked(autostart.is_enabled())

    def _save(self):
        s = self._settings
        s.set("gemini_api_key",  self._gemini_key.text().strip())
        s.set("claude_api_key",  self._claude_key.text().strip())
        s.set("turso_db_url",    self._turso_url.text().strip())
        s.set("turso_auth_token", self._turso_token.text().strip())
        s.set("hotkey",          self._hotkey_widget.current_key())
        s.set("ai_model_provider", "claude" if self._radio_claude.isChecked() else "gemini")
        s.set("gemini_ai_model", self._gemini_model.currentText())
        s.set("claude_ai_model", self._claude_model.currentText())
        s.set("stt_model",       self._stt_model.currentText())
        s.set("remove_fillers",  self._toggle_fillers.isChecked())
        s.set("fix_grammar",     self._toggle_grammar.isChecked())
        s.set("auto_translate",  self._toggle_translate.isChecked())
        s.set("translation_language", self._translate_lang.currentText())
        s.set("tone_adjustment_enabled", self._toggle_tone.isChecked())
        s.set("tone_adjustment_value",   self._tone_value.currentText().lower())
        self._pipeline.reconfigure()

        self._saved_lbl.setVisible(True)
        self._save_timer.start(3000)

    def _on_hotkey_captured(self, key: str):
        pass

    def _on_autostart_toggled(self, enabled: bool):
        ok = autostart.set_enabled(enabled)
        if not ok:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Autostart", "Could not update Windows registry.")
            self._toggle_autostart.setChecked(autostart.is_enabled())

    # ── API tests ─────────────────────────────────────────────────────────────

    def _test_gemini(self):
        from PyQt6.QtWidgets import QMessageBox
        ok = GeminiClient(
            self._gemini_key.text().strip(),
            self._gemini_model.currentText(),
            self._gemini_model.currentText(),
        ).test_connection()
        if ok:
            QMessageBox.information(self, "Gemini", "Connection successful!")
        else:
            QMessageBox.warning(self, "Gemini", "Connection failed. Check your API key.")

    def _test_claude(self):
        from PyQt6.QtWidgets import QMessageBox
        ok = ClaudeClient(
            self._claude_key.text().strip(),
            self._claude_model.currentText(),
        ).test_connection()
        if ok:
            QMessageBox.information(self, "Claude", "Connection successful!")
        else:
            QMessageBox.warning(self, "Claude", "Connection failed. Check your API key.")

    def _test_turso(self):
        from PyQt6.QtWidgets import QMessageBox
        from voiceflow.storage.history_db import HistoryDB
        db = HistoryDB(self._turso_url.text().strip(), self._turso_token.text().strip())
        if db.is_enabled:
            QMessageBox.information(self, "Turso", "Schema initialized successfully!")
        else:
            QMessageBox.warning(self, "Turso", "Could not connect. Check URL and token.")
