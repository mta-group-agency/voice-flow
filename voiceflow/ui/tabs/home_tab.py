"""
Home tab — default landing view.
Shows monthly stats, per-day bar chart, and 3 most-recent transcriptions.
"""
from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from voiceflow.storage.history_db import HistoryDB
from voiceflow.ui import theme

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


# ── Stat card ─────────────────────────────────────────────────────────────────

class _StatCard(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("stat_card")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(2)

        self._title_lbl = QLabel(title.upper())
        self._title_lbl.setObjectName("stat_label")

        self._value_lbl = QLabel("—")
        self._value_lbl.setObjectName("stat_value")

        self._unit_lbl = QLabel("")
        self._unit_lbl.setObjectName("stat_unit")

        lay.addWidget(self._title_lbl)
        lay.addWidget(self._value_lbl)
        lay.addWidget(self._unit_lbl)

    def set_value(self, value: str, unit: str = ""):
        self._value_lbl.setText(value)
        self._unit_lbl.setText(unit)


# ── Bar chart ─────────────────────────────────────────────────────────────────

class _BarChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[tuple[int, int]] = []
        self._today = datetime.now().day
        self.setMinimumHeight(110)

    def set_data(self, data: list[tuple[int, int]]):
        self._data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = theme.get_tokens()

        if not self._data:
            painter.setPen(QColor(t["text_4"]))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No data for this month")
            return

        w, h = self.width(), self.height()
        axis_h = 20
        chart_h = h - axis_h
        max_val = max(v for _, v in self._data) or 1
        n = len(self._data)
        gap = 3
        bar_w = max(4, min(14, (w - gap) // n - gap))

        for i, (day, count) in enumerate(self._data):
            x = i * (bar_w + gap)
            is_today = day == self._today

            if count == 0:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(t["hairline"]))
                painter.drawRoundedRect(x, chart_h - 3, bar_w, 3, 1, 1)
            else:
                bar_h = max(4, int((count / max_val) * (chart_h - 4)))
                y = chart_h - bar_h
                grad = QLinearGradient(x, y, x, chart_h)
                grad.setColorAt(0, QColor(t["accent"]))
                grad.setColorAt(1, QColor(t["accent_deep"]))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(grad)
                painter.drawRoundedRect(x, y, bar_w, bar_h, 2, 2)
                if is_today:
                    pen = QPen(QColor(t["accent"]))
                    pen.setWidth(2)
                    painter.setPen(pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRoundedRect(x - 2, y - 2, bar_w + 4, bar_h + 4, 3, 3)

            if day in {1, 5, 10, 15, 20, 25, 31}:
                painter.setPen(QColor(t["text_4"]))
                painter.drawText(x, h - 2, str(day))


# ── Transcript card ────────────────────────────────────────────────────────────

class _TranscriptCard(QFrame):
    def __init__(self, entry: dict, primary_copy: bool = False, parent=None):
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
        if primary_copy:
            copy_btn.setObjectName("primary")
            copy_btn.setFixedWidth(80)
        else:
            copy_btn.setObjectName("ghost")
            copy_btn.setFixedWidth(70)
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(text))
        actions.addWidget(copy_btn)
        lay.addLayout(actions)


# ── Home tab ──────────────────────────────────────────────────────────────────

class HomeTab(QWidget):
    view_all_clicked = pyqtSignal()

    def __init__(self, db: HistoryDB, parent=None):
        super().__init__(parent)
        self._db = db
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        inner = QWidget()
        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._lay = QVBoxLayout(inner)
        self._lay.setContentsMargins(28, 22, 28, 24)
        self._lay.setSpacing(16)

        # Greeting row
        now = datetime.now()
        hour = now.hour
        time_of_day = "morning" if hour < 12 else ("afternoon" if hour < 18 else "evening")
        greeting_row = QHBoxLayout()
        g_lbl = QLabel(f"Good {time_of_day}")
        g_lbl.setObjectName("greeting")
        period_lbl = QLabel(f"{MONTH_NAMES[now.month]} {now.year}")
        period_lbl.setObjectName("meta_label")
        greeting_row.addWidget(g_lbl)
        greeting_row.addStretch()
        greeting_row.addWidget(period_lbl)
        self._lay.addLayout(greeting_row)

        # Stat grid
        grid = QHBoxLayout()
        grid.setSpacing(10)
        self._card_sessions = _StatCard("Sessions")
        self._card_audio    = _StatCard("Audio Time")
        self._card_chars    = _StatCard("Characters")
        self._card_cost     = _StatCard("Est. Cost")
        for c in (self._card_sessions, self._card_audio, self._card_chars, self._card_cost):
            grid.addWidget(c)
        self._lay.addLayout(grid)

        # Chart card
        chart_card = QFrame()
        chart_card.setObjectName("card")
        cl = QVBoxLayout(chart_card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(8)
        ch = QHBoxLayout()
        chart_title = QLabel("Sessions per day")
        chart_title.setStyleSheet(
            "font-size: 13px; font-weight: 600; background: transparent;"
        )
        self._chart_sub = QLabel("")
        self._chart_sub.setObjectName("meta_label")
        ch.addWidget(chart_title)
        ch.addStretch()
        ch.addWidget(self._chart_sub)
        cl.addLayout(ch)
        self._chart = _BarChart()
        cl.addWidget(self._chart)
        self._lay.addWidget(chart_card)

        # Recent dictations header
        recent_row = QHBoxLayout()
        rl = QLabel("RECENT DICTATIONS")
        rl.setObjectName("section_label")
        view_all = QPushButton("View all →")
        view_all.setObjectName("ghost")
        view_all.setFixedWidth(90)
        view_all.clicked.connect(self.view_all_clicked.emit)
        recent_row.addWidget(rl)
        recent_row.addStretch()
        recent_row.addWidget(view_all)
        self._lay.addLayout(recent_row)

        # Recent cards container
        self._recent_w = QWidget()
        self._recent_lay = QVBoxLayout(self._recent_w)
        self._recent_lay.setContentsMargins(0, 0, 0, 0)
        self._recent_lay.setSpacing(10)
        self._lay.addWidget(self._recent_w)

        # No-DB placeholder
        self._no_db = QLabel(
            "Database not configured.\nAdd Turso URL and token in Settings."
        )
        self._no_db.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_db.setObjectName("hint")
        self._lay.addWidget(self._no_db)
        self._lay.addStretch()

    def refresh(self):
        try:
            self._refresh()
        except Exception:
            pass

    def _refresh(self):
        now = datetime.now()

        if self._db.is_enabled:
            self._no_db.hide()
            stats = self._db.get_stats(now.year, now.month)
            sessions  = sum(s.sessions      for s in stats)
            audio_s   = sum(s.total_audio_s for s in stats)
            chars     = sum(s.total_chars   for s in stats)
            cost      = sum(s.cost_usd      for s in stats)

            mins, secs = divmod(int(audio_s), 60)
            audio_str = f"{mins}:{secs:02d}" if mins else f"{audio_s:.0f}s"

            self._card_sessions.set_value(str(sessions))
            self._card_audio.set_value(audio_str, "min·sec" if mins else "seconds")
            self._card_chars.set_value(f"{chars:,}")
            self._card_cost.set_value(f"${cost:.4f}", "USD")

            daily = self._db.get_daily_sessions(now.year, now.month)
            if daily:
                peak = max(daily, key=lambda x: x[1])
                avg  = sum(v for _, v in daily) / len(daily)
                self._chart_sub.setText(
                    f"avg {avg:.1f}/day · peak {peak[1]} on day {peak[0]}"
                )
            self._chart.set_data(daily)
            entries = self._db.get_recent(limit=3)
        else:
            self._no_db.show()
            for c in (self._card_sessions, self._card_audio, self._card_chars, self._card_cost):
                c.set_value("—")
            self._chart.set_data([])
            entries = []

        # Clear old cards
        while self._recent_lay.count():
            item = self._recent_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for entry in entries:
            self._recent_lay.addWidget(_TranscriptCard(entry, primary_copy=True))
