from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)

from voiceflow.storage.history_db import HistoryDB, MonthStats

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class _StatCard(QWidget):
    def __init__(self, title: str, value: str, unit: str = "", parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)
        self.setStyleSheet("border: 2px solid #000000; background-color: #FFFFFF;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        self._title_lbl = QLabel(title.upper())
        self._title_lbl.setStyleSheet(
            "font-size: 10px; font-weight: 700; color: #666666; border: none; letter-spacing: 1px;"
        )
        self._value_lbl = QLabel(value)
        self._value_lbl.setStyleSheet(
            "font-size: 28px; font-weight: 900; color: #000000; border: none;"
        )
        self._unit_lbl = QLabel(unit)
        self._unit_lbl.setStyleSheet(
            "font-size: 11px; color: #666666; border: none;"
        )

        layout.addWidget(self._title_lbl)
        layout.addWidget(self._value_lbl)
        layout.addWidget(self._unit_lbl)

    def update_value(self, value: str, unit: str = ""):
        self._value_lbl.setText(value)
        self._unit_lbl.setText(unit)


class _BarChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[tuple[int, int]] = []  # (day, count)
        self.setMinimumHeight(120)

    def set_data(self, data: list[tuple[int, int]]):
        self._data = data
        self.update()

    def paintEvent(self, event):
        if not self._data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        margin = 8
        max_val = max(v for _, v in self._data) or 1
        bar_w = max(4, (w - 2 * margin) // len(self._data) - 2)

        for i, (day, count) in enumerate(self._data):
            bar_h = int((count / max_val) * (h - 30))
            x = margin + i * (bar_w + 2)
            y = h - 20 - bar_h

            painter.setBrush(QColor("#FFDD00"))
            painter.setPen(QPen(QColor("#000000"), 1))
            painter.drawRect(x, y, bar_w, bar_h)

            if len(self._data) <= 15:
                painter.setPen(QColor("#666666"))
                painter.drawText(x, h - 4, str(day))


class StatsTab(QWidget):
    def __init__(self, db: HistoryDB, parent=None):
        super().__init__(parent)
        self._db = db
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Month selector
        top = QHBoxLayout()
        top.addWidget(QLabel("Month:"))
        self._month_combo = QComboBox()
        self._month_combo.setFixedWidth(200)
        self._month_combo.currentIndexChanged.connect(self._load_stats)
        top.addWidget(self._month_combo)
        top.addStretch()
        layout.addLayout(top)

        # Stat cards
        cards_row = QHBoxLayout()
        self._card_sessions = _StatCard("Sessions", "—")
        self._card_audio = _StatCard("Audio Time", "—", "seconds")
        self._card_chars = _StatCard("Characters", "—")
        self._card_cost = _StatCard("Est. Cost", "—", "USD")
        for card in (self._card_sessions, self._card_audio, self._card_chars, self._card_cost):
            cards_row.addWidget(card)
        layout.addLayout(cards_row)

        # Chart
        chart_lbl = QLabel("Sessions per day")
        chart_lbl.setStyleSheet("font-weight: 700; font-size: 13px;")
        layout.addWidget(chart_lbl)

        self._chart = _BarChart()
        layout.addWidget(self._chart, 1)

        self._no_db_lbl = QLabel(
            "Database not configured.\nAdd Turso URL and token in Settings."
        )
        self._no_db_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_db_lbl.setStyleSheet("color: #888888; font-size: 13px;")
        layout.addWidget(self._no_db_lbl)

    def refresh(self):
        self._populate_months()
        self._load_stats()

    def _populate_months(self):
        self._month_combo.blockSignals(True)
        self._month_combo.clear()

        months = self._db.get_available_months() if self._db.is_enabled else []
        now = datetime.now()
        if not months or (now.year, now.month) not in months:
            months.insert(0, (now.year, now.month))

        for year, month in months:
            self._month_combo.addItem(f"{MONTH_NAMES[month]} {year}", (year, month))

        self._month_combo.blockSignals(False)

    def _load_stats(self):
        data = self._month_combo.currentData()
        if not data:
            return
        year, month = data

        if not self._db.is_enabled:
            self._no_db_lbl.show()
            return
        self._no_db_lbl.hide()

        stats: list[MonthStats] = self._db.get_stats(year, month)

        total_sessions = sum(s.sessions for s in stats)
        total_audio = sum(s.total_audio_s for s in stats)
        total_chars = sum(s.total_chars for s in stats)
        total_cost = sum(s.cost_usd for s in stats)

        self._card_sessions.update_value(str(total_sessions))
        self._card_audio.update_value(f"{total_audio:.0f}", "seconds")
        self._card_chars.update_value(f"{total_chars:,}")
        self._card_cost.update_value(f"${total_cost:.4f}", "USD")

        # Chart: sessions per day (simulated from total for now)
        # Real per-day breakdown would need a separate DB query
        self._chart.set_data([])
