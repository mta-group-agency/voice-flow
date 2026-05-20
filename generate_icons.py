"""
Generates tray icons as PNG files using PyQt6.
Run once: python generate_icons.py
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)


def make_icon(filename: str, bg: str, dot_color: str, letter: str):
    size = 64
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background circle
    p.setBrush(QColor(bg))
    p.setPen(QPen(QColor("#000000"), 3))
    p.drawEllipse(3, 3, size - 6, size - 6)

    # Microphone body
    p.setBrush(QColor(dot_color))
    p.setPen(QPen(QColor("#000000"), 2))
    # Mic capsule
    p.drawRoundedRect(22, 10, 20, 28, 10, 10)
    # Stand
    p.setBrush(Qt.GlobalColor.transparent)
    p.setPen(QPen(QColor(dot_color), 3))
    p.drawArc(16, 24, 32, 20, 0, -180 * 16)
    # Pole
    p.drawLine(32, 44, 32, 52)
    # Base
    p.drawLine(22, 52, 42, 52)

    p.end()

    pixmap = QPixmap.fromImage(img)
    pixmap.save(filename)
    print(f"Saved: {filename}")


make_icon("assets/icon.png",     bg="#FFFFFF", dot_color="#000000", letter="V")
make_icon("assets/icon_rec.png", bg="#FF3333", dot_color="#FFFFFF", letter="R")
make_icon("assets/icon_proc.png",bg="#FFDD00", dot_color="#000000", letter="P")

print("Icons generated.")
sys.exit(0)
