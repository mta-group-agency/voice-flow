from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

import voiceflow.core.logger as logger
from voiceflow.storage.history_db import HistoryDB

_log = logger.get(__name__)


class _EntryCard(QWidget):
    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(
            "QWidget#card { background-color: #FFFFFF; border: 1px solid #E4E4E7;"
            " border-radius: 8px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Header row: time + duration
        top_row = QHBoxLayout()
        created = str(entry.get("created_at", ""))[:19]
        duration = entry.get("duration_s") or 0
        time_lbl = QLabel(created)
        time_lbl.setStyleSheet("font-size: 11px; color: #666666; border: none;")
        dur_lbl = QLabel(f"{float(duration):.1f}s")
        dur_lbl.setStyleSheet("font-size: 11px; color: #666666; border: none;")
        top_row.addWidget(time_lbl)
        top_row.addStretch()
        top_row.addWidget(dur_lbl)
        layout.addLayout(top_row)

        # Final text
        text = str(entry.get("final_text", ""))
        text_lbl = QLabel(text)
        text_lbl.setWordWrap(True)
        text_lbl.setStyleSheet("font-size: 13px; color: #000000; border: none;")
        layout.addWidget(text_lbl)

        # Copy button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("secondary")
        copy_btn.setFixedWidth(70)
        copy_btn.clicked.connect(lambda: self._copy(text))
        btn_row.addWidget(copy_btn)
        layout.addLayout(btn_row)

    def _copy(self, text: str):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)


class HistoryTab(QWidget):
    def __init__(self, db: HistoryDB, parent=None):
        super().__init__(parent)
        self._db = db
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("Recent Transcriptions")
        title.setStyleSheet("font-weight: 700; font-size: 14px;")
        clear_btn = QPushButton("Clear History")
        clear_btn.setObjectName("danger")
        clear_btn.setFixedWidth(130)
        clear_btn.clicked.connect(self._clear)
        top.addWidget(title)
        top.addStretch()
        top.addWidget(clear_btn)
        layout.addLayout(top)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(self._scroll.Shape.NoFrame)
        self._inner = QWidget()
        self._inner_layout = QVBoxLayout(self._inner)
        self._inner_layout.setContentsMargins(0, 0, 0, 0)
        self._inner_layout.setSpacing(6)
        self._inner_layout.addStretch()
        self._scroll.setWidget(self._inner)
        layout.addWidget(self._scroll)

        self._empty_lbl = QLabel("No transcriptions yet.\nStart recording with your hotkey!")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet("color: #888888; font-size: 13px;")

        self.refresh()

    def refresh(self):
        try:
            self._refresh()
        except Exception:
            _log.exception("History tab refresh failed")

    def _refresh(self):
        # Clear previous cards — skip _empty_lbl so we can reuse it safely
        while self._inner_layout.count() > 1:
            item = self._inner_layout.takeAt(0)
            w = item.widget()
            if w is not None and w is not self._empty_lbl:
                w.deleteLater()

        if not self._db.is_enabled:
            self._empty_lbl.setText(
                "Database not configured.\nAdd Turso URL and token in Settings."
            )
            self._inner_layout.insertWidget(0, self._empty_lbl)
            return

        entries = self._db.get_recent(limit=10)
        _log.debug("History: loaded %d entries", len(entries))
        if not entries:
            self._empty_lbl.setText("No transcriptions yet.\nStart recording with your hotkey!")
            self._inner_layout.insertWidget(0, self._empty_lbl)
            return

        for entry in entries:
            card = _EntryCard(entry)
            self._inner_layout.insertWidget(self._inner_layout.count() - 1, card)

    def _clear(self):
        reply = QMessageBox.question(
            self, "Clear History", "Delete all transcription history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.clear_history()
            self.refresh()
