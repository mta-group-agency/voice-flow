"""
Small always-on-top overlay shown when recording / processing.
Shows a live level meter (equalizer bars) during recording.
"""

import random

from PyQt6.QtCore import QPoint, QPropertyAnimation, Qt, QTimer, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from voiceflow.ui import theme


class _LevelMeter(QWidget):
    BAR_COUNT = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(42, 30)
        self._bars = [0.0] * self.BAR_COUNT
        self._decay = QTimer(self)
        self._decay.setInterval(40)
        self._decay.timeout.connect(self._tick)
        self._decay.start()

    def set_level(self, level: float):
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

        t = theme.get_tokens()
        h = self.height()
        bar_w = 5
        gap = (self.width() - self.BAR_COUNT * bar_w) // (self.BAR_COUNT - 1)

        for i, lvl in enumerate(self._bars):
            bh = max(6, int(lvl * h))
            x = i * (bar_w + gap)
            y = h - bh
            color = QColor(t["success"]) if lvl > 0.08 else QColor(t["text_4"])
            painter.setBrush(color)
            painter.drawRoundedRect(x, y, bar_w, bh, 2, 2)


class _PulsingDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self._opacity = 1.0
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
        t = theme.get_tokens()
        color = QColor(t["accent"])
        color.setAlphaF(self._opacity)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(1, 1, 14, 14)


class RecordingOverlay(QWidget):
    cancel_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("overlay_root")
        self.setFixedSize(240, 54)
        self._apply_stylesheet()

        self._meter = _LevelMeter(self)
        self._dot   = _PulsingDot(self)
        self._label = QLabel("Recording", self)
        self._label.setObjectName("overlay_text")
        self._timer_label = QLabel("0:00", self)
        self._timer_label.setObjectName("overlay_timer")
        self._stop_btn = QPushButton("Stop", self)
        self._stop_btn.setObjectName("overlay_stop")
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.setToolTip("Stop processing (Esc)")
        self._stop_btn.clicked.connect(self.cancel_requested.emit)
        self._stop_btn.setVisible(False)

        row = QHBoxLayout()
        row.setContentsMargins(14, 0, 14, 0)
        row.setSpacing(10)
        row.addWidget(self._meter)
        row.addWidget(self._dot)
        row.addWidget(self._label)
        row.addStretch()
        row.addWidget(self._timer_label)
        row.addWidget(self._stop_btn)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addLayout(row)

        self._elapsed = 0
        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._on_tick)

        self._drag_pos: QPoint | None = None
        self._position_bottom_right()

        self._meter.setVisible(False)
        self._dot.setVisible(False)

    def _apply_stylesheet(self):
        from voiceflow.ui.theme import build_overlay_stylesheet, get_active
        self.setStyleSheet(build_overlay_stylesheet(get_active()))

    def set_theme(self, theme_name: str):
        self._apply_stylesheet()
        for w in (self._label, self._timer_label, self._stop_btn):
            w.style().unpolish(w)
            w.style().polish(w)
        self.update()

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
        self._stop_btn.setVisible(False)
        self._timer_label.setVisible(True)
        self._tick.start()
        self.show()
        self.raise_()

    def show_processing(self):
        self._tick.stop()
        self._label.setText("Processing…")
        self._meter.setVisible(False)
        self._dot.setVisible(True)
        self._timer_label.setText("")
        self._timer_label.setVisible(False)
        self._stop_btn.setVisible(True)
        self.show()
        self.raise_()

    def hide_overlay(self):
        self._tick.stop()
        self._stop_btn.setVisible(False)
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
        t = theme.get_tokens()

        # Warm dark background
        bg = QColor(t["bg_titlebar"])
        bg.setAlpha(230)
        painter.setBrush(bg)

        # Subtle accent border
        accent = QColor(t["accent"])
        accent.setAlpha(40)
        pen = QPen(accent)
        pen.setWidth(1)
        painter.setPen(pen)

        painter.drawRoundedRect(0, 0, self.width() - 1, self.height() - 1, 12, 12)
