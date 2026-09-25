"""
Shared modal dialog for onboarding popups: pre-update info, post-update "what's
new" and the first-run welcome. Inherits the global application stylesheet.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QPointF, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import (
    QBrush, QColor, QDesktopServices, QPainter, QPainterPath, QPen, QPixmap,
    QTextCharFormat, QTextCursor,
)
from PyQt6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QTextBrowser,
    QVBoxLayout,
)

from voiceflow.platform import IS_MAC
from voiceflow.ui import theme

_GIF_WIDTH = 432
_GIF_HEIGHT = 220
_GIF_MIN_HEIGHT = 110
_BODY_MIN_HEIGHT = 160
_BODY_FLOOR_HEIGHT = 100
_BODY_MAX_HEIGHT = 480
# Covers the native title bar (~31 px on Windows 11 at 100%) plus slack; the
# dialog geometry Qt reports excludes the frame.
_SCREEN_SAFETY_MARGIN = 48

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


def _apply_link_color(browser: QTextBrowser, color: str) -> None:
    # setMarkdown() colors anchors from the application palette, ignoring
    # document.setDefaultStyleSheet() — the char format has to be set directly.
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    cursor = QTextCursor(browser.document())
    block = browser.document().begin()
    while block.isValid():
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            if fragment.isValid() and fragment.charFormat().isAnchor():
                cursor.setPosition(fragment.position())
                cursor.setPosition(
                    fragment.position() + fragment.length(), QTextCursor.MoveMode.KeepAnchor
                )
                cursor.mergeCharFormat(fmt)
            it += 1
        block = block.next()


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
        self._title_lbl = title_lbl
        self._video_btn: Optional[QPushButton] = None

        if video_url:
            self._gif_label = _ClickableLabel()
            self._gif_label.setObjectName("gif_thumb")
            self._gif_label.setFixedSize(_GIF_WIDTH, _GIF_HEIGHT)
            self._gif_label.setScaledContents(True)
            self._gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._gif_label.setCursor(Qt.CursorShape.PointingHandCursor)
            # Visible from the start so the dialog never grows (and pushes the
            # buttons off-screen) when the thumbnail arrives after it is shown.
            self._gif_label.setText("Ładowanie podglądu…")
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
            self._gif_worker.failed.connect(self._on_gif_failed)
            self._gif_worker.start()

        browser = QTextBrowser()
        browser.setObjectName("dialog_body")
        browser.setMarkdown(body)
        _apply_link_color(browser, theme.get_link_color())
        browser.setOpenExternalLinks(True)
        browser.setMinimumHeight(_BODY_FLOOR_HEIGHT)
        browser.setMaximumHeight(_BODY_MAX_HEIGHT)
        lay.addWidget(browser)
        self._body_browser = browser

        if video_url:
            video_btn = QPushButton("▶ Obejrzyj pełne wideo")
            video_btn.setObjectName("ghost")
            video_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(video_url)))
            lay.addWidget(video_btn)
            self._video_btn = video_btn

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
        self._button_row = row
        self._fit_body_height()

    def showEvent(self, event):
        # Fit and apply the final size before QDialog.showEvent positions the
        # window: any growth after that extends downward, past the screen edge.
        self._fit_body_height()
        self.layout().activate()
        super().showEvent(event)

    def _fit_title_height(self) -> int:
        # A word-wrapped QLabel doesn't raise the window's minimum height to its
        # wrapped text, so a long title got squeezed over the widgets below it.
        margins = self.layout().contentsMargins()
        width = self._title_lbl.width() if self.isVisible() else 0
        if width <= 0:
            width = max(self.minimumWidth(), self.layout().sizeHint().width())
            width -= margins.left() + margins.right()
        height = self._title_lbl.heightForWidth(width)
        self._title_lbl.setMinimumHeight(height)
        return height

    def _max_body_height(self) -> int:
        screen = self.screen() or QApplication.primaryScreen()
        margins = self.layout().contentsMargins()
        other = margins.top() + margins.bottom() + self._fit_title_height()
        gaps = 2  # title-body, body-buttons

        if self._video_url:
            other += self._video_btn.sizeHint().height()
            gaps += 2  # gif label and video button each add one more gap

        other += self._button_row.sizeHint().height()
        other += self.layout().spacing() * gaps
        other += _SCREEN_SAFETY_MARGIN

        free = screen.availableGeometry().height() - other if screen else 10_000

        if self._gif_label is not None:
            gif_height = max(_GIF_MIN_HEIGHT, min(_GIF_HEIGHT, free - _BODY_MIN_HEIGHT))
            self._gif_label.setFixedSize(_GIF_WIDTH * gif_height // _GIF_HEIGHT, gif_height)
            free -= gif_height

        return max(_BODY_FLOOR_HEIGHT, min(_BODY_MAX_HEIGHT, free))

    def _fit_body_height(self):
        # QTextBrowser doesn't grow to its document by itself: without this the
        # welcome text (added as the "Jak zacząć" step grew) got clipped behind a
        # fixed max-height and needed scrolling to reach the Groq key step.
        self.ensurePolished()
        browser = self._body_browser
        doc = browser.document()
        width = browser.viewport().width()
        if width <= 0:
            doc_margin = int(doc.documentMargin()) * 2
            width = max(self.minimumWidth() - 48 - 24 - 2 - doc_margin, 240)
        doc.setTextWidth(width)
        content_height = int(doc.size().height())
        chrome = 30  # QSS border (1px*2) + padding (10px top/bottom) + rounding slack
        max_height = self._max_body_height()
        total = min(max(_BODY_MIN_HEIGHT, content_height + chrome), max_height)
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
            self._on_gif_failed()
            return
        pm = self._with_play_overlay(pm)
        self._gif_label.setPixmap(pm)

    def _on_gif_failed(self):
        if self._gif_label is not None and self._gif_label.pixmap().isNull():
            self._gif_label.setText("Podgląd niedostępny, kliknij, aby obejrzeć wideo")
