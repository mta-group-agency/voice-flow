"""
Shared modal dialog for onboarding popups: pre-update info, post-update "what's
new" and the first-run welcome. Inherits the global application stylesheet.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QPointF, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import (
    QBrush, QColor, QDesktopServices, QPainter, QPainterPath, QPen, QPixmap,
)
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QTextBrowser, QVBoxLayout,
)

from voiceflow.platform import IS_MAC
from voiceflow.ui import theme

_GIF_WIDTH = 432
_GIF_HEIGHT = 220
_BODY_MIN_HEIGHT = 160
_BODY_MAX_HEIGHT = 480

WELCOME_TITLE = "Witaj w VoiceFlow"
WELCOME_BODY = (
    "Mówisz, pojawia się gotowy tekst tam, gdzie akurat piszesz. Bez przepisywania, "
    "bez przeklikiwania.\n\n"
    "**Jak zacząć:**\n\n"
    "1. Otwórz **Ustawienia (Settings) > API Keys**, wklej darmowy klucz Groq z "
    "[console.groq.com/keys](https://console.groq.com/keys) i kliknij **Test**.\n"
    "2. Przytrzymaj **prawy Alt**, mów, puść.\n\n"
    "**Dwa tryby:**\n\n"
    "- **Prawy Alt: dyktowanie.** Przytrzymaj, powiedz co chcesz, puść: transkrypcja "
    "wkleja się sama.\n"
    "- **Drugi hotkey: Asystent AI.** Powiedz polecenie (np. \"odpisz grzecznie, że nie "
    "dam rady\"), a AI wykona je i wklei gotowy wynik. Opcjonalny, ustawisz go później, "
    "jeśli będzie potrzebny.\n\n"
    "Tyle. Wracaj tu kiedy chcesz. VoiceFlow czeka w tle."
)
if IS_MAC:
    WELCOME_BODY = (
        WELCOME_BODY
        .replace("Prawy Alt", "Prawy Option")
        .replace("prawy Alt", "prawy Option")
    )
WELCOME_VIDEO_URL = ""  # uzupelnij linkiem Loom, gdy powstanie walkthrough


class _ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class _GifWorker(QThread):
    loaded = pyqtSignal(bytes)
    failed = pyqtSignal()

    def __init__(self, video_url: str, parent=None):
        super().__init__(parent)
        self._video_url = video_url

    def run(self):
        try:
            from voiceflow.core import updater
            import requests
            gif_url = updater.loom_gif_url(self._video_url)
            if not gif_url:
                self.failed.emit()
                return
            r = requests.get(gif_url, timeout=10)
            r.raise_for_status()
            self.loaded.emit(r.content)
        except Exception:
            self.failed.emit()


class WhatsNewDialog(QDialog):
    def __init__(
        self,
        title: str,
        body: str,
        video_url: Optional[str] = None,
        mode: str = "post_update",
        parent=None,
    ):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)

        self._video_url = video_url
        self._gif_worker: Optional[_GifWorker] = None
        self._gif_label: Optional[_ClickableLabel] = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("dialog_title")
        title_lbl.setWordWrap(True)
        lay.addWidget(title_lbl)

        if video_url:
            self._gif_label = _ClickableLabel()
            self._gif_label.setObjectName("gif_thumb")
            self._gif_label.setFixedWidth(_GIF_WIDTH)
            self._gif_label.setFixedHeight(_GIF_HEIGHT)
            self._gif_label.setScaledContents(True)
            self._gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._gif_label.setCursor(Qt.CursorShape.PointingHandCursor)
            self._gif_label.hide()
            self._gif_label.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl(video_url))
            )
            lay.addWidget(self._gif_label, alignment=Qt.AlignmentFlag.AlignHCenter)

            # No Qt parent: a QThread parented to this dialog would be force-deleted
            # mid-run if it's closed (or the app quits) before the fetch finishes
            # ("QThread: Destroyed while thread is still running" — a fatal abort).
            # self._gif_worker keeps it alive.
            self._gif_worker = _GifWorker(video_url)
            self._gif_worker.loaded.connect(self._on_gif_loaded)
            self._gif_worker.start()

        browser = QTextBrowser()
        browser.setObjectName("dialog_body")
        accent = theme.get_accent()
        browser.document().setDefaultStyleSheet(f"a {{ color: {accent}; }}")
        browser.setMarkdown(body)
        browser.setOpenExternalLinks(True)
        browser.setMinimumHeight(_BODY_MIN_HEIGHT)
        browser.setMaximumHeight(_BODY_MAX_HEIGHT)
        lay.addWidget(browser)
        self._body_browser = browser
        self._fit_body_height()

        if video_url:
            video_btn = QPushButton("▶ Obejrzyj pełne wideo")
            video_btn.setObjectName("ghost")
            video_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(video_url)))
            lay.addWidget(video_btn)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addStretch()

        if mode == "pre_update":
            later_btn = QPushButton("Później")
            later_btn.setObjectName("ghost")
            later_btn.clicked.connect(self.reject)
            primary_btn = QPushButton("Aktualizuj teraz")
            primary_btn.setObjectName("primary")
            primary_btn.clicked.connect(self.accept)
            row.addWidget(later_btn)
            row.addWidget(primary_btn)
        elif mode == "welcome":
            primary_btn = QPushButton("Zaczynam")
            primary_btn.setObjectName("primary")
            primary_btn.clicked.connect(self.accept)
            row.addWidget(primary_btn)
        else:
            primary_btn = QPushButton("Świetnie, zaczynam")
            primary_btn.setObjectName("primary")
            primary_btn.clicked.connect(self.accept)
            row.addWidget(primary_btn)

        lay.addLayout(row)

    def showEvent(self, event):
        super().showEvent(event)
        self._fit_body_height()

    def _fit_body_height(self):
        # QTextBrowser doesn't grow to its document by itself: without this the
        # welcome text (added as the "Jak zacząć" step grew) got clipped behind a
        # fixed max-height and needed scrolling to reach the Groq key step.
        browser = self._body_browser
        doc = browser.document()
        width = browser.viewport().width()
        if width <= 0:
            doc_margin = int(doc.documentMargin()) * 2
            width = max(self.minimumWidth() - 48 - 24 - 2 - doc_margin, 240)
        doc.setTextWidth(width)
        content_height = int(doc.size().height())
        chrome = 30  # QSS border (1px*2) + padding (10px top/bottom) + rounding slack
        total = max(_BODY_MIN_HEIGHT, min(content_height + chrome, _BODY_MAX_HEIGHT))
        browser.setMinimumHeight(total)
        browser.setMaximumHeight(total)

    def _with_play_overlay(self, pixmap: QPixmap) -> QPixmap:
        result = QPixmap(pixmap)
        w, h = result.width(), result.height()
        r = int(min(w, h) * 0.13)
        cx, cy = w // 2, h // 2

        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(QColor(0, 0, 0, 120)))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        triangle = QPainterPath()
        triangle.moveTo(cx - r * 0.35, cy - r * 0.55)
        triangle.lineTo(cx - r * 0.35, cy + r * 0.55)
        triangle.lineTo(cx + r * 0.6, cy)
        triangle.closeSubpath()
        painter.setBrush(QBrush(QColor(255, 255, 255, 235)))
        painter.drawPath(triangle)

        painter.end()
        return result

    def _on_gif_loaded(self, data: bytes):
        if not data or self._gif_label is None:
            return
        pm = QPixmap()
        if not pm.loadFromData(data):
            return
        pm = self._with_play_overlay(pm)
        self._gif_label.setPixmap(pm)
        self._gif_label.show()
