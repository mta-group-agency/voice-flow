APP_STYLESHEET = """
/* ── Base ── */
QWidget {
    background-color: #F8F8FA;
    color: #18181B;
    font-family: "Inter", "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
}

/* ── Custom title bar ── */
QWidget#title_bar {
    background-color: #18181B;
}

QLabel#title_label {
    color: #FAFAFA;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 1.5px;
    background: transparent;
}

QLabel#title_version {
    color: #71717A;
    font-size: 11px;
    font-weight: 400;
    background: transparent;
}

QPushButton#wnd_btn {
    background-color: transparent;
    color: #71717A;
    border: none;
    border-radius: 4px;
    font-size: 15px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    padding: 0;
}

QPushButton#wnd_btn:hover {
    background-color: #3F3F46;
    color: #FAFAFA;
}

QPushButton#wnd_btn_close:hover {
    background-color: #DC2626;
    color: #FFFFFF;
}

/* ── Tabs ── */
QTabWidget::pane {
    border: none;
    background-color: #F8F8FA;
}

QTabBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E4E4E7;
}

QTabBar::tab {
    background-color: transparent;
    color: #71717A;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 11px 28px;
    font-weight: 500;
    font-size: 13px;
    min-width: 80px;
}

QTabBar::tab:selected {
    color: #18181B;
    font-weight: 600;
    border-bottom: 2px solid #FFDD00;
    background-color: transparent;
}

QTabBar::tab:hover:!selected {
    color: #3F3F46;
    background-color: #F4F4F5;
}

/* ── Buttons ── */
QPushButton {
    background-color: #FFDD00;
    color: #18181B;
    border: none;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: 600;
    font-size: 13px;
    min-height: 34px;
}

QPushButton:hover {
    background-color: #EAB308;
}

QPushButton:pressed {
    background-color: #CA8A04;
}

QPushButton:disabled {
    background-color: #E4E4E7;
    color: #A1A1AA;
}

QPushButton#danger {
    background-color: #FEE2E2;
    color: #DC2626;
    border: 1px solid #FECACA;
}

QPushButton#danger:hover {
    background-color: #DC2626;
    color: #FFFFFF;
    border-color: #DC2626;
}

QPushButton#secondary {
    background-color: #F4F4F5;
    color: #3F3F46;
    border: 1px solid #E4E4E7;
}

QPushButton#secondary:hover {
    background-color: #E4E4E7;
    color: #18181B;
    border-color: #D4D4D8;
}

/* ── Input fields ── */
QLineEdit {
    border: 1px solid #E4E4E7;
    border-radius: 6px;
    padding: 7px 10px;
    background-color: #FFFFFF;
    color: #18181B;
    font-size: 13px;
    selection-background-color: #FEF08A;
    selection-color: #18181B;
}

QLineEdit:focus {
    border: 1.5px solid #FFDD00;
    outline: none;
}

QLineEdit:disabled {
    background-color: #F4F4F5;
    color: #A1A1AA;
    border-color: #E4E4E7;
}

/* ── ComboBox ── */
QComboBox {
    border: 1px solid #E4E4E7;
    border-radius: 6px;
    padding: 6px 10px;
    background-color: #FFFFFF;
    color: #18181B;
    font-size: 13px;
    min-height: 34px;
}

QComboBox:focus {
    border: 1.5px solid #FFDD00;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    border: 1px solid #E4E4E7;
    border-radius: 6px;
    background-color: #FFFFFF;
    selection-background-color: #FEF9C3;
    selection-color: #18181B;
    outline: none;
    padding: 4px;
}

QComboBox:disabled {
    background-color: #F4F4F5;
    color: #A1A1AA;
}

/* ── Radio / CheckBox ── */
QRadioButton {
    font-size: 13px;
    spacing: 8px;
    color: #3F3F46;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1.5px solid #D4D4D8;
    border-radius: 8px;
    background-color: #FFFFFF;
}

QRadioButton::indicator:checked {
    background-color: #FFDD00;
    border-color: #EAB308;
}

/* ── Group Box ── */
QGroupBox {
    border: none;
    border-top: 1px solid #E4E4E7;
    border-radius: 0px;
    margin-top: 24px;
    padding-top: 14px;
    font-weight: 600;
    font-size: 11px;
    color: #A1A1AA;
    letter-spacing: 0.8px;
    background-color: transparent;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    background-color: #F8F8FA;
    color: #A1A1AA;
    font-size: 11px;
    font-weight: 600;
}

/* ── Labels ── */
QLabel#hint {
    color: #A1A1AA;
    font-size: 11px;
}

/* ── Scroll bars ── */
QScrollBar:vertical {
    background-color: transparent;
    width: 6px;
    margin: 0;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: #D4D4D8;
    border-radius: 3px;
    min-height: 32px;
}

QScrollBar::handle:vertical:hover {
    background-color: #A1A1AA;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
}

/* ── Scrollable area ── */
QScrollArea {
    border: none;
    background-color: transparent;
}

/* ── Status bar ── */
QStatusBar {
    background-color: #FFFFFF;
    border-top: 1px solid #E4E4E7;
    font-size: 11px;
    color: #71717A;
    padding: 0 4px;
    min-height: 28px;
}

/* ── History cards ── */
QWidget#card {
    background-color: #FFFFFF;
    border: 1px solid #E4E4E7;
    border-radius: 8px;
}

/* ── Tooltip ── */
QToolTip {
    background-color: #18181B;
    color: #FAFAFA;
    border: none;
    border-radius: 4px;
    padding: 5px 10px;
    font-size: 12px;
}
"""

OVERLAY_STYLESHEET = """
QWidget#overlay_root {
    background-color: rgba(24, 24, 27, 220);
    border-radius: 10px;
}

QLabel#overlay_text {
    color: #FAFAFA;
    font-weight: 600;
    font-size: 13px;
    font-family: "Inter", "Segoe UI", sans-serif;
    background: transparent;
}

QLabel#overlay_timer {
    color: #FFDD00;
    font-weight: 600;
    font-size: 12px;
    font-family: "Inter", "Segoe UI", sans-serif;
    background: transparent;
}
"""
