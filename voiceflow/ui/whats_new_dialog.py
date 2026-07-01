"""
Shared modal dialog for onboarding popups: pre-update info, post-update "what's
new" and the first-run welcome. Inherits the global application stylesheet.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QTextBrowser, QVBoxLayout,
)

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

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("dialog_title")
        title_lbl.setWordWrap(True)
        lay.addWidget(title_lbl)

        browser = QTextBrowser()
        browser.setObjectName("dialog_body")
        browser.setMarkdown(body)
        browser.setOpenExternalLinks(True)
        browser.setMinimumHeight(220)
        browser.setMaximumHeight(320)
        lay.addWidget(browser)

        if video_url:
            video_btn = QPushButton("▶ Zobacz walkthrough")
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
