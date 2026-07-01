"""
Shared modal dialog for onboarding popups: pre-update info, post-update "what's
new" and the first-run welcome. Inherits the global application stylesheet.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QTextBrowser, QVBoxLayout,
)

_GIF_WIDTH = 432
_GIF_HEIGHT = 220

WELCOME_TITLE = "Witaj w VoiceFlow"
WELCOME_BODY = (
    "Mówisz — pojawia się gotowy tekst tam, gdzie akurat piszesz. Bez przepisywania, "
    "bez przeklikiwania.\n\n"
    "**Dwa tryby:**\n\n"
    "- **Prawy Alt — dyktowanie.** Przytrzymaj, powiedz co chcesz, puść — transkrypcja "
    "wkleja się sama.\n"
    "- **Drugi hotkey — Asystent AI.** Powiedz polecenie (np. \"odpisz grzecznie, że nie "
    "dam rady\"), a AI wykona je i wklei gotowy wynik.\n\n"
    "**Jak zacząć (1 minuta):**\n\n"
    "1. Otwórz **Ustawienia**.\n"
    "2. Ustaw oba hotkeye pod siebie.\n"
    "3. Dla zera kosztów wybierz **Groq** i wklej darmowy klucz API.\n\n"
    "Tyle. Wracaj tu kiedy chcesz — VoiceFlow czeka w tle."
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

            self._gif_worker = _GifWorker(video_url, self)
            self._gif_worker.loaded.connect(self._on_gif_loaded)
            self._gif_worker.start()

        browser = QTextBrowser()
        browser.setObjectName("dialog_body")
        browser.setMarkdown(body)
        browser.setOpenExternalLinks(True)
        browser.setMinimumHeight(220)
        browser.setMaximumHeight(320)
        lay.addWidget(browser)

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

    def _on_gif_loaded(self, data: bytes):
        if not data or self._gif_label is None:
            return
        pm = QPixmap()
        if not pm.loadFromData(data):
            return
        self._gif_label.setPixmap(pm)
        self._gif_label.show()
