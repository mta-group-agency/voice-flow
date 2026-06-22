"""
Main application window — frameless, custom title bar + tab bar.
Tabs: Home (default) | History | Settings.
"""
from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QColor, QKeyEvent, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel,
    QMainWindow, QPushButton, QSizeGrip, QStackedWidget,
    QVBoxLayout, QWidget,
)

from voiceflow.__version__ import __version__
from voiceflow.ui import theme
from voiceflow.ui.tabs.history_tab import HistoryTab
from voiceflow.ui.tabs.home_tab import HomeTab
from voiceflow.ui.tabs.settings_tab import SettingsTab
from voiceflow.ui.update_banner import UpdateBanner


class _BrandMark(QWidget):
    """18×18 amber rounded-square with 3 white bars."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(18, 18)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = theme.get_tokens()
        grad = QLinearGradient(0, 0, 0, 18)
        grad.setColorAt(0, QColor(t["accent"]))
        grad.setColorAt(1, QColor(t["accent_deep"]))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 18, 18, 4, 4)
        painter.setBrush(QColor(t["on_accent"]))
        for x, y, w, h in ((3, 5, 12, 2), (3, 9, 8, 2), (3, 13, 10, 2)):
            painter.drawRoundedRect(x, y, w, h, 1, 1)


class _GlowDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(7, 7)
        self._state = "ready"

    def set_state(self, state: str):
        self._state = state
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = theme.get_tokens()
        color = {"recording": t["danger"], "processing": t["accent"]}.get(self._state, t["success"])
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 7, 7)


class _TitleBar(QWidget):
    def __init__(self, window: QMainWindow):
        super().__init__(window)
        self._win = window
        self._drag_pos: QPoint | None = None
        self.setObjectName("title_bar")
        self.setFixedHeight(38)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 8, 0)
        lay.setSpacing(8)

        lay.addWidget(_BrandMark(self))
        name_lbl = QLabel("VoiceFlow")
        name_lbl.setObjectName("title_brand")
        ver_lbl = QLabel(f"v{__version__}")
        ver_lbl.setObjectName("title_version")
        lay.addWidget(name_lbl)
        lay.addSpacing(2)
        lay.addWidget(ver_lbl)
        lay.addStretch()

        pill = QWidget()
        pill.setObjectName("status_pill")
        pill_lay = QHBoxLayout(pill)
        pill_lay.setContentsMargins(10, 3, 10, 3)
        pill_lay.setSpacing(6)
        self._dot = _GlowDot(pill)
        pill_lay.addWidget(self._dot)
        self._pill_label = QLabel("Ready · press hotkey to dictate")
        self._pill_label.setObjectName("status_pill_text")
        pill_lay.addWidget(self._pill_label)
        lay.addWidget(pill)

        lay.addStretch()

        for obj, sym, tip, slot in (
            ("wnd_btn",       "−", "Minimize",      window.showMinimized),
            ("wnd_btn",       "□", "Maximize",       lambda: window.showNormal() if window.isMaximized() else window.showMaximized()),
            ("wnd_btn_close", "✕", "Close to tray",  window.hide),
        ):
            btn = QPushButton(sym)
            btn.setObjectName(obj)
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            lay.addWidget(btn)
        lay.addSpacing(4)

    def set_status(self, text: str, state: str = "ready"):
        self._pill_label.setText(text)
        self._dot.set_state(state)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self._win.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self._win.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        self._win.showNormal() if self._win.isMaximized() else self._win.showMaximized()


class _TabButton(QPushButton):
    """Tab button with amber underline when checked, drawn via paintEvent."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setObjectName("tab_btn")
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.isChecked():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.get_accent()))
            r = self.rect()
            painter.drawRect(10, r.height() - 2, r.width() - 20, 2)


class _TabBar(QWidget):
    tab_changed = pyqtSignal(int)
    theme_toggled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tab_bar")
        self.setFixedHeight(44)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 0)
        lay.setSpacing(2)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        for idx, label in enumerate(("Home", "History", "Settings")):
            btn = _TabButton(label, self)
            self._group.addButton(btn, idx)
            lay.addWidget(btn)
            btn.clicked.connect(lambda _, i=idx: self.tab_changed.emit(i))

        self._group.button(0).setChecked(True)
        lay.addStretch()

        self._theme_btn = QPushButton("☀", self)
        self._theme_btn.setObjectName("tab_icon_btn")
        self._theme_btn.setToolTip("Toggle theme (dark / light)")
        self._theme_btn.clicked.connect(self.theme_toggled.emit)
        lay.addWidget(self._theme_btn)
        lay.addSpacing(4)

    def set_active(self, idx: int):
        btn = self._group.button(idx)
        if btn:
            btn.setChecked(True)

    def update_theme_icon(self, theme_name: str):
        self._theme_btn.setText("☀" if theme_name == "dark" else "🌙")


class _StatusBar(QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setObjectName("status_bar")
        self.setFixedHeight(28)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(8)

        self._dot = QLabel("●")
        self._dot.setObjectName("status_bar_text")
        self._state_lbl = QLabel("Ready")
        self._state_lbl.setObjectName("status_bar_text")
        sep = QLabel("·")
        sep.setObjectName("status_bar_text")

        cfg = settings.config
        model = cfg.claude_ai_model if cfg.ai_model_provider == "claude" else cfg.gemini_ai_model
        self._model_pill = QLabel(model)
        self._model_pill.setObjectName("status_bar_pill")

        lay.addWidget(self._dot)
        lay.addWidget(self._state_lbl)
        lay.addWidget(sep)
        lay.addWidget(self._model_pill)
        lay.addStretch()
        lay.addWidget(QSizeGrip(self))

        self._update_dot(theme.get_tokens()["success"])

    def set_state(self, text: str, state: str):
        self._state_lbl.setText(text)
        t = theme.get_tokens()
        color = {"recording": t["danger"], "processing": t["accent"]}.get(state, t["success"])
        self._update_dot(color)

    def refresh_model(self, cfg):
        if cfg.ai_model_provider == "claude":
            model = cfg.claude_ai_model
        elif cfg.ai_model_provider == "groq":
            model = cfg.groq_ai_model
        else:
            model = cfg.gemini_ai_model
        self._model_pill.setText(model)

    def _update_dot(self, color: str):
        self._dot.setStyleSheet(
            f"color: {color}; background: transparent;"
            f" font-family: 'Cascadia Mono', 'Consolas', monospace; font-size: 11px;"
        )


class _BorderOverlay(QWidget):
    """1px dark border drawn on top of all content, transparent to mouse events."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAutoFillBackground(False)

    def paintEvent(self, event):
        painter = QPainter(self)
        pen = QPen(QColor(0, 0, 0, 55))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)


class MainWindow(QMainWindow):
    theme_changed = pyqtSignal(str)

    def __init__(self, settings, db, pipeline):
        super().__init__()
        self._settings = settings
        self._pipeline = pipeline
        self._current_theme = "dark"

        self.setWindowTitle("VoiceFlow")
        self.setMinimumSize(920, 680)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._title_bar = _TitleBar(self)
        root.addWidget(self._title_bar)

        self._tab_bar = _TabBar(self)
        self._tab_bar.tab_changed.connect(self._on_tab_switched)
        self._tab_bar.theme_toggled.connect(self._toggle_theme)
        root.addWidget(self._tab_bar)

        self._update_banner = UpdateBanner(self)
        banner_wrap = QWidget()
        bw_lay = QVBoxLayout(banner_wrap)
        bw_lay.setContentsMargins(28, 14, 28, 0)
        bw_lay.setSpacing(0)
        bw_lay.addWidget(self._update_banner)
        root.addWidget(banner_wrap)

        self._stack = QStackedWidget()
        self._home_tab = HomeTab(db)
        self._history_tab = HistoryTab(db)
        self._settings_tab = SettingsTab(settings, pipeline)
        self._stack.addWidget(self._home_tab)
        self._stack.addWidget(self._history_tab)
        self._stack.addWidget(self._settings_tab)
        root.addWidget(self._stack)

        self._status_bar = _StatusBar(settings, self)
        root.addWidget(self._status_bar)

        self._home_tab.view_all_clicked.connect(lambda: self._switch_tab(1))
        self._settings_tab.theme_requested.connect(self.set_theme)
        self._settings_tab.settings_saved.connect(
            lambda: self._status_bar.refresh_model(settings.config)
        )

        pipeline.state_changed.connect(self._on_state_changed)
        pipeline.error_occurred.connect(self._on_error)
        pipeline.history_updated.connect(self._on_history_updated)

        self._border_overlay = _BorderOverlay(central)

    def show_update_banner(self, info):
        self._update_banner.show_update(info)

    def trigger_update(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self._update_banner.start_update_now()

    def connect_restart(self, slot):
        self._update_banner.restart_requested.connect(slot)

    def _on_tab_switched(self, idx: int):
        self._stack.setCurrentIndex(idx)
        w = self._stack.currentWidget()
        if hasattr(w, "refresh"):
            w.refresh()

    def _switch_tab(self, idx: int):
        self._tab_bar.set_active(idx)
        self._on_tab_switched(idx)

    def _toggle_theme(self):
        self.set_theme("light" if self._current_theme == "dark" else "dark")

    def set_theme(self, mode: str):
        if mode not in ("dark", "light"):
            mode = "dark"
        self._current_theme = mode
        theme.set_active(mode)
        self._tab_bar.update_theme_icon(mode)
        self._settings_tab.update_theme_buttons(mode)
        self._settings.set("theme", mode)
        self.theme_changed.emit(mode)

    def _on_state_changed(self, state):
        from voiceflow.core.pipeline import State
        state_map = {
            State.IDLE:         ("Ready · press hotkey to dictate", "ready"),
            State.RECORDING:    ("Recording…",          "recording"),
            State.TRANSCRIBING: ("Transcribing…",        "processing"),
            State.PROCESSING:   ("Processing with AI…",  "processing"),
            State.INJECTING:    ("Injecting text…",      "processing"),
        }
        text, s = state_map.get(state, ("", "ready"))
        self._title_bar.set_status(text, s)
        self._status_bar.set_state(text, s)

    def _on_error(self, msg: str):
        self._title_bar.set_status(msg, "ready")
        self._status_bar.set_state(msg, "ready")

    def _on_history_updated(self):
        if self._stack.currentIndex() == 1:
            self._history_tab.refresh()
        self._home_tab.refresh()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_dwm_shadow()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._border_overlay.setGeometry(self.centralWidget().rect())
        self._border_overlay.raise_()

    def _apply_dwm_shadow(self):
        import ctypes
        from ctypes import Structure, c_int, byref

        class MARGINS(Structure):
            _fields_ = [
                ("cxLeftWidth", c_int), ("cxRightWidth", c_int),
                ("cyTopHeight", c_int), ("cyBottomHeight", c_int),
            ]

        try:
            ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(
                int(self.winId()), byref(MARGINS(1, 1, 1, 1))
            )
        except Exception:
            pass

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self._pipeline.cancel()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent):
        event.ignore()
        self.hide()
