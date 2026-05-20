"""
Small always-on-top overlay shown when recording / processing.
Shows a live level meter (equalizer bars) during recording.
"""

import random

from PyQt6.QtCore import QPoint, QPropertyAnimation, Qt, QTimer, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from voiceflow.ui.styles import OVERLAY_STYLESHEET


class _LevelMeter(QWidget):
    """5-bar equalizer driven by live microphone amplitude."""

    BAR_COUNT = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(42, 30)
        self._bars = [0.0] * self.BAR_COUNT
        self._decay = QTimer(self)
        self._decay.setInterval(40)  # 25 fps decay
        self._decay.timeout.connect(self._tick)
        self._decay.start()

    def set_level(self, level: float):
        # Power curve: makes quiet speech fill more of the bar visually
        boosted = min(1.0, (level ** 0.4) * 1.1)
        for i in range(self.BAR_COUNT):
            target = min(1.0, boosted * random.uniform(0.55, 1.0))
            if target > self._bars[i]:
                self._bars[i] = target
        self.update()

    def _tick(self):
        changed = False
        for i in range(self.BAR_COUNT):
            if self._bars[i] > 0.05:
                self._bars[i] = max(0.0, self._bars[i] - 0.08)
                changed = True
        if changed:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        h = self.height()
        bar_w = 5
        gap = (self.width() - self.BAR_COUNT * bar_w) // (self.BAR_COUNT - 1)

        for i, lvl in enumerate(self._bars):
            bh = max(6, int(lvl * h))  # minimum 6px so bars are always visible
            x = i * (bar_w + gap)
            y = h - bh
            color = QColor("#4ADE80") if lvl > 0.08 else QColor("#374151")
            painter.setBrush(color)
            painter.drawRoundedRect(x, y, bar_w, bh, 2, 2)


class _PulsingDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self._opacity = 1.0
        self._color = QColor("#FFDD00")
        self._anim = QPropertyAnimation(self, b"dot_opacity")
        self._anim.setDuration(700)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.2)
        self._anim.setLoopCount(-1)
        self._anim.start()

    def get_dot_opacity(self):
        return self._opacity

    def set_dot_opacity(self, val):
        self._opacity = val
        self.update()

    dot_opacity = pyqtProperty(float, get_dot_opacity, set_dot_opacity)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self._color)
        color.setAlphaF(self._opacity)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(1, 1, 14, 14)


class RecordingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("overlay_root")
        self.setStyleSheet(OVERLAY_STYLESHEET)
        self.setFixedSize(230, 52)

        self._meter = _LevelMeter(self)
        self._dot = _PulsingDot(self)
        self._label = QLabel("Recording", self)
        self._label.setObjectName("overlay_text")
        self._timer_label = QLabel("0:00", self)
        self._timer_label.setObjectName("overlay_timer")

        row = QHBoxLayout()
        row.setContentsMargins(12, 0, 12, 0)
        row.setSpacing(10)
        row.addWidget(self._meter)
        row.addWidget(self._dot)
        row.addWidget(self._label)
        row.addStretch()
        row.addWidget(self._timer_label)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addLayout(row)

        self._elapsed = 0
        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._on_tick)

        self._drag_pos: QPoint | None = None
        self._position_bottom_right()

        # Start hidden
        self._meter.setVisible(False)
        self._dot.setVisible(False)

    def _position_bottom_right(self):
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.right() - self.width() - 20, geo.bottom() - self.height() - 50)

    def set_level(self, level: float):
        self._meter.set_level(level)

    def show_recording(self):
        self._elapsed = 0
        self._timer_label.setText("0:00")
        self._label.setText("Recording")
        self._meter.setVisible(True)
        self._dot.setVisible(False)
        self._tick.start()
        self.show()
        self.raise_()

    def show_processing(self):
        self._tick.stop()
        self._label.setText("Processing…")
        self._meter.setVisible(False)
        self._dot.setVisible(True)
        self._timer_label.setText("")

    def hide_overlay(self):
        self._tick.stop()
        self.hide()

    def _on_tick(self):
        self._elapsed += 1
        mins = self._elapsed // 60
        secs = self._elapsed % 60
        self._timer_label.setText(f"{mins}:{secs:02d}")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(24, 24, 27, 220))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 10, 10)
