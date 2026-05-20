"""
Animated toggle switch widget painted via QPainter.
"""

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget


class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    _W, _H = 48, 26

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setFixedSize(self._W, self._H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._checked = checked
        self._handle_x = float(self._W - self._H + 3) if checked else 3.0

        self._anim = QPropertyAnimation(self, b"handle_x")
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def get_handle_x(self) -> float:
        return self._handle_x

    def set_handle_x(self, val: float):
        self._handle_x = val
        self.update()

    handle_x = pyqtProperty(float, get_handle_x, set_handle_x)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked == checked:
            return
        self._checked = checked
        self._animate()

    def _animate(self):
        target = float(self._W - self._H + 3) if self._checked else 3.0
        self._anim.stop()
        self._anim.setStartValue(self._handle_x)
        self._anim.setEndValue(target)
        self._anim.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self._animate()
            self.toggled.emit(self._checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Track
        track_color = QColor("#000000") if self._checked else QColor("#BBBBBB")
        painter.setBrush(track_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 4, self._W, self._H - 8, 9, 9)

        # Handle
        h_size = self._H - 6
        painter.setBrush(QColor("#FFDD00") if self._checked else QColor("#FFFFFF"))
        from PyQt6.QtGui import QPen
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.drawEllipse(int(self._handle_x), 3, h_size, h_size)
