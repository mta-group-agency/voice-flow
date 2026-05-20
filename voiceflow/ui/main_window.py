"""
Main application window with three tabs: Settings, History, Stats.
Frameless window with custom title bar. Hides to tray on close.
"""

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QCloseEvent, QColor
from PyQt6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
    QPushButton, QSizeGrip, QMainWindow, QTabWidget, QVBoxLayout, QWidget,
)

from voiceflow.ui.tabs.history_tab import HistoryTab
from voiceflow.ui.tabs.settings_tab import SettingsTab
from voiceflow.ui.tabs.stats_tab import StatsTab


class _TitleBar(QWidget):
    def __init__(self, window: QMainWindow):
        super().__init__(window)
        self._win = window
        self._drag_pos: QPoint | None = None
        self.setObjectName("title_bar")
        self.setFixedHeight(46)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(6)

        name_lbl = QLabel("VOICEFLOW")
        name_lbl.setObjectName("title_label")
        ver_lbl = QLabel("v1.0")
        ver_lbl.setObjectName("title_version")
        layout.addWidget(name_lbl)
        layout.addSpacing(6)
        layout.addWidget(ver_lbl)
        layout.addStretch()

        min_btn = QPushButton("−")
        min_btn.setObjectName("wnd_btn")
        min_btn.setToolTip("Minimize")
        min_btn.clicked.connect(window.showMinimized)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("wnd_btn")
        close_btn.setToolTip("Close to tray")
        close_btn.setStyleSheet(
            "QPushButton { color: #71717A; background: transparent; border: none; border-radius: 4px;"
            " font-size: 14px; min-width: 32px; max-width: 32px; min-height: 32px; max-height: 32px; }"
            "QPushButton:hover { background-color: #DC2626; color: #FFFFFF; }"
        )
        close_btn.clicked.connect(window.hide)

        layout.addWidget(min_btn)
        layout.addWidget(close_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self._win.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self._win.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        if self._win.isMaximized():
            self._win.showNormal()
        else:
            self._win.showMaximized()


class MainWindow(QMainWindow):
    def __init__(self, settings, db, pipeline):
        super().__init__()
        self._settings = settings
        self._db = db
        self._pipeline = pipeline

        self.setWindowTitle("VoiceFlow")
        self.setMinimumSize(740, 560)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Outer transparent shell — gives shadow room to render
        shell = QWidget()
        shell.setStyleSheet("background: transparent;")
        self.setCentralWidget(shell)
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(10, 10, 10, 10)  # shadow margin

        # Inner card — gets the drop shadow
        central = QFrame()
        central.setStyleSheet("QFrame { background-color: #F8F8FA; border-radius: 8px; }")
        shadow = QGraphicsDropShadowEffect(central)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 60))
        central.setGraphicsEffect(shadow)
        shell_layout.addWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(_TitleBar(self))

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._settings_tab = SettingsTab(settings, pipeline)
        self._history_tab = HistoryTab(db)
        self._stats_tab = StatsTab(db)

        self._tabs.addTab(self._settings_tab, "Settings")
        self._tabs.addTab(self._history_tab, "History")
        self._tabs.addTab(self._stats_tab, "Stats")
        self._tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(self._tabs)

        # Bottom bar: status + resize grip
        bottom = QWidget()
        bottom.setFixedHeight(26)
        bottom.setStyleSheet("background-color: #FFFFFF; border-top: 1px solid #E4E4E7;")
        bottom_row = QHBoxLayout(bottom)
        bottom_row.setContentsMargins(10, 0, 0, 0)
        bottom_row.setSpacing(0)
        self._status_lbl = QLabel("VoiceFlow running — press the hotkey to dictate")
        self._status_lbl.setStyleSheet("color: #71717A; font-size: 11px;")
        bottom_row.addWidget(self._status_lbl)
        bottom_row.addStretch()
        bottom_row.addWidget(QSizeGrip(self))
        root.addWidget(bottom)

        pipeline.state_changed.connect(self._on_state_changed)
        pipeline.error_occurred.connect(self._on_error)
        pipeline.history_updated.connect(self._on_history_updated)

    def _on_tab_changed(self, index: int):
        widget = self._tabs.widget(index)
        if hasattr(widget, "refresh"):
            widget.refresh()

    def _on_state_changed(self, state):
        from voiceflow.core.pipeline import State
        labels = {
            State.IDLE: "Ready — press hotkey to dictate",
            State.RECORDING: "Recording…",
            State.TRANSCRIBING: "Transcribing…",
            State.PROCESSING: "Processing with AI…",
            State.INJECTING: "Injecting text…",
        }
        self._status_lbl.setText(labels.get(state, ""))

    def _on_error(self, msg: str):
        self._status_lbl.setText(msg)

    def _on_history_updated(self):
        if self._tabs.currentIndex() == 1:
            self._history_tab.refresh()

    def closeEvent(self, event: QCloseEvent):
        event.ignore()
        self.hide()
