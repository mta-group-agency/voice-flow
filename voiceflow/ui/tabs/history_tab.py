from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

import voiceflow.core.logger as logger
from voiceflow.storage.history_db import HistoryDB

_log = logger.get(__name__)


class _EntryCard(QFrame):
    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("transcript_card")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)

        created = str(entry.get("created_at", ""))[:19]
        duration = float(entry.get("duration_s") or 0)

        date_lbl = QLabel(created)
        date_lbl.setObjectName("card_date")
        dur_lbl = QLabel(f"{duration:.1f}s")
        dur_lbl.setObjectName("card_duration")

        text = str(entry.get("final_text", ""))
        chars_lbl = QLabel(f"{len(text)} chars")
        chars_lbl.setObjectName("meta_label")

        header.addWidget(date_lbl)
        header.addWidget(dur_lbl)
        header.addStretch()
        header.addWidget(chars_lbl)
        lay.addLayout(header)

        body = QLabel(text)
        body.setObjectName("card_body")
        body.setWordWrap(True)
        lay.addWidget(body)

        actions = QHBoxLayout()
        actions.addStretch()
        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("ghost")
        copy_btn.setFixedWidth(70)
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(text))
        actions.addWidget(copy_btn)
        lay.addLayout(actions)


class HistoryTab(QWidget):
    def __init__(self, db: HistoryDB, parent=None):
        super().__init__(parent)
        self._db = db
        self._all_entries: list[dict] = []
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 20, 28, 20)
        lay.setSpacing(12)

        # Header row
        header = QHBoxLayout()
        title = QLabel("RECENT TRANSCRIPTIONS")
        title.setObjectName("section_label")
        header.addWidget(title)
        header.addStretch()
        lay.addLayout(header)

        # Toolbar: search + clear
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        from PyQt6.QtWidgets import QLineEdit
        self._search = QLineEdit()
        self._search.setObjectName("search_input")
        self._search.setPlaceholderText("Search transcriptions…")
        self._search.textChanged.connect(self._on_search)

        clear_btn = QPushButton("Clear History")
        clear_btn.setObjectName("danger_ghost")
        clear_btn.setFixedWidth(130)
        clear_btn.clicked.connect(self._clear)

        toolbar.addWidget(self._search)
        toolbar.addWidget(clear_btn)
        lay.addLayout(toolbar)

        # Scrollable card list
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(self._scroll.Shape.NoFrame)
        self._inner = QWidget()
        self._inner_lay = QVBoxLayout(self._inner)
        self._inner_lay.setContentsMargins(0, 0, 0, 0)
        self._inner_lay.setSpacing(10)
        self._inner_lay.addStretch()
        self._scroll.setWidget(self._inner)
        lay.addWidget(self._scroll)

        self._empty_lbl = QLabel("No transcriptions yet.\nStart recording with your hotkey!")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setObjectName("hint")

        self.refresh()

    def refresh(self):
        try:
            self._all_entries = self._db.get_recent(limit=50) if self._db.is_enabled else []
            self._render(self._all_entries)
        except Exception:
            _log.exception("History tab refresh failed")

    def _on_search(self, text: str):
        if not text:
            self._render(self._all_entries)
            return
        q = text.lower()
        filtered = [e for e in self._all_entries if q in str(e.get("final_text", "")).lower()]
        self._render(filtered)

    def _render(self, entries: list[dict]):
        while self._inner_lay.count() > 1:
            item = self._inner_lay.takeAt(0)
            w = item.widget()
            if w and w is not self._empty_lbl:
                w.deleteLater()

        if not self._db.is_enabled:
            self._empty_lbl.setText(
                "Database not configured.\nAdd Turso URL and token in Settings."
            )
            self._inner_lay.insertWidget(0, self._empty_lbl)
            return

        if not entries:
            self._empty_lbl.setText(
                "No transcriptions yet.\nStart recording with your hotkey!"
                if not self._search.text()
                else "No results match your search."
            )
            self._inner_lay.insertWidget(0, self._empty_lbl)
            return

        for entry in entries:
            self._inner_lay.insertWidget(self._inner_lay.count() - 1, _EntryCard(entry))

    def _clear(self):
        reply = QMessageBox.question(
            self, "Clear History", "Delete all transcription history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.clear_history()
            self._all_entries = []
            self.refresh()
