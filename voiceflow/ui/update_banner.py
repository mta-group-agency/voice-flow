"""
Update check/download workers and the in-window update banner.
"""
from __future__ import annotations

import webbrowser

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout,
)

from voiceflow.__version__ import __version__
from voiceflow.core import updater
from voiceflow.core.updater import UpdateInfo


class UpdateCheckWorker(QThread):
    update_found = pyqtSignal(object)

    def run(self):
        info = updater.check_for_update()
        if info and info.update_available:
            self.update_found.emit(info)


class UpdateDownloadWorker(QThread):
    progress = pyqtSignal(int)
    finished_ok = pyqtSignal()
    failed = pyqtSignal()

    def __init__(self, info: UpdateInfo, parent=None):
        super().__init__(parent)
        self._info = info

    def run(self):
        if updater.apply_update(self._info, self.progress.emit):
            self.finished_ok.emit()
        else:
            self.failed.emit()


class UpdateBanner(QFrame):
    restart_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("update_banner")
        self._info: UpdateInfo | None = None
        self._worker: UpdateDownloadWorker | None = None
        self.hide()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(8)

        row = QHBoxLayout()
        row.setSpacing(12)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self._text = QLabel()
        self._text.setObjectName("update_text")
        self._sub = QLabel()
        self._sub.setObjectName("update_sub")
        text_col.addWidget(self._text)
        text_col.addWidget(self._sub)
        row.addLayout(text_col)
        row.addStretch()

        self._update_btn = QPushButton("Update")
        self._update_btn.setObjectName("primary")
        self._update_btn.setFixedWidth(110)
        self._update_btn.clicked.connect(self._start_update)
        self._later_btn = QPushButton("Later")
        self._later_btn.setObjectName("ghost")
        self._later_btn.setFixedWidth(80)
        self._later_btn.clicked.connect(self.hide)
        row.addWidget(self._update_btn)
        row.addWidget(self._later_btn)
        lay.addLayout(row)

        self._progress = QProgressBar()
        self._progress.setObjectName("update_progress")
        self._progress.setRange(0, 100)
        self._progress.hide()
        lay.addWidget(self._progress)

    def show_update(self, info: UpdateInfo):
        self._info = info
        self._text.setText(f"Update available {info.latest_version}")
        self._sub.setText(f"You have {__version__}")
        self._progress.hide()
        self._update_btn.setEnabled(True)
        self._later_btn.show()
        self._update_btn.setText("Update")
        self.show()

    def start_update_now(self):
        if self._info is not None:
            self.show()
            self._start_update()

    def _start_update(self):
        if self._info is None:
            return
        self._update_btn.setEnabled(False)
        self._later_btn.hide()
        self._update_btn.setText("Downloading…")
        self._progress.setValue(0)
        self._progress.show()

        self._worker = UpdateDownloadWorker(self._info, self)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_finished(self):
        self._text.setText("Update ready — restarting…")
        self.restart_requested.emit()

    def _on_failed(self):
        self._progress.hide()
        self._text.setText("Downloading update in your browser…")
        self._sub.setText("When it's done, close VoiceFlow and run the downloaded file.")
        self._update_btn.hide()
        self._later_btn.setText("Close")
        self._later_btn.show()
        if self._info is not None:
            webbrowser.open(self._info.download_url or self._info.html_url)
