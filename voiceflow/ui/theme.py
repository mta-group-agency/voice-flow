"""
Design tokens and QSS generator for VoiceFlow v2.
Two themes: "dark" (default) and "light".
Qt QSS has no variables — stylesheet is built at runtime via string formatting.
"""
from __future__ import annotations

DARK: dict[str, str] = {
    "bg_app":        "#211F1E",
    "bg_titlebar":   "#1B1A19",
    "bg_statusbar":  "#1E1C1B",
    "surface_1":     "#2B2826",
    "surface_2":     "#34302E",
    "surface_hover": "#3B3733",
    "border":        "#3F3B37",
    "border_strong": "#524C46",
    "hairline":      "#33302D",
    "text_1":        "#F6F4F1",
    "text_2":        "#B1ACA4",
    "text_3":        "#7B756D",
    "text_4":        "#5A554F",
    "accent":        "#EFC233",
    "accent_deep":   "#D9A91A",
    "on_accent":     "#252220",
    "success":       "#5CC58A",
    "danger":        "#E66A4C",
}

LIGHT: dict[str, str] = {
    "bg_app":        "#F8F6F2",
    "bg_titlebar":   "#EFECE6",
    "bg_statusbar":  "#F1EFEA",
    "surface_1":     "#FFFFFF",
    "surface_2":     "#FBFAF7",
    "surface_hover": "#F2F0EB",
    "border":        "#DCD8D1",
    "border_strong": "#B8B2A7",
    "hairline":      "#E8E4DC",
    "text_1":        "#28241F",
    "text_2":        "#534D45",
    "text_3":        "#7B756D",
    "text_4":        "#A29B91",
    "accent":        "#D9A91A",
    "accent_deep":   "#B8881A",
    "on_accent":     "#272218",
    "success":       "#2E9E5E",
    "danger":        "#C4422A",
}

TOKENS: dict[str, dict[str, str]] = {"dark": DARK, "light": LIGHT}
_active: str = "dark"


def get_active() -> str:
    return _active


def set_active(theme: str) -> None:
    global _active
    if theme in TOKENS:
        _active = theme


def get_accent() -> str:
    return TOKENS[_active]["accent"]


def get_tokens(theme: str | None = None) -> dict[str, str]:
    return TOKENS.get(theme or _active, DARK)


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{int(alpha * 255)})"


def build_stylesheet(theme: str = "dark") -> str:
    t = TOKENS.get(theme, DARK)
    dark = theme == "dark"

    scroll_thumb   = _rgba("#FFFFFF", 0.08) if dark else _rgba("#000000", 0.10)
    scroll_thumb_h = _rgba("#FFFFFF", 0.16) if dark else _rgba("#000000", 0.18)
    tint1 = _rgba("#FFFFFF", 0.04) if dark else _rgba("#000000", 0.03)

    acc10 = _rgba(t["accent"], 0.10)
    acc18 = _rgba(t["accent"], 0.18)
    acc35 = _rgba(t["accent"], 0.35)
    acc50 = _rgba(t["accent"], 0.50)
    dng10 = _rgba(t["danger"], 0.10)
    dng30 = _rgba(t["danger"], 0.30)
    dng55 = _rgba(t["danger"], 0.55)

    return f"""
/* ── Base ─────────────────────────────── */
QWidget {{
    background-color: {t['bg_app']};
    color: {t['text_1']};
    font-family: "Segoe UI Variable", "Segoe UI", sans-serif;
    font-size: 13px;
    border: none;
    outline: 0;
}}

/* ── Title bar ─────────────────────────── */
QWidget#title_bar {{
    background-color: {t['bg_titlebar']};
    border-bottom: 1px solid {t['hairline']};
}}
QLabel#title_brand {{
    color: {t['text_1']};
    font-weight: 600;
    font-size: 12px;
    background: transparent;
}}
QLabel#title_version {{
    color: {t['text_4']};
    font-size: 11px;
    font-family: "Cascadia Mono", "Consolas", monospace;
    background: transparent;
}}
QFrame#status_pill {{
    background-color: {tint1};
    border: 1px solid {t['hairline']};
    border-radius: 999px;
}}
QLabel#status_pill_text {{
    color: {t['text_2']};
    font-size: 11px;
    background: transparent;
}}
QPushButton#wnd_btn {{
    background: transparent; color: {t['text_3']};
    border: none; border-radius: 5px; font-size: 14px;
    min-width: 28px; max-width: 28px;
    min-height: 24px; max-height: 24px; padding: 0;
}}
QPushButton#wnd_btn:hover {{ background: {tint1}; color: {t['text_1']}; }}
QPushButton#wnd_btn_close {{
    background: transparent; color: {t['text_3']};
    border: none; border-radius: 5px; font-size: 12px;
    min-width: 28px; max-width: 28px;
    min-height: 24px; max-height: 24px; padding: 0;
}}
QPushButton#wnd_btn_close:hover {{ background: {t['danger']}; color: #FFFFFF; }}

/* ── Tab bar ────────────────────────────── */
QWidget#tab_bar {{
    background-color: {t['bg_app']};
    border-bottom: 1px solid {t['hairline']};
}}
QPushButton#tab_btn {{
    background: transparent; color: {t['text_3']};
    border: none; border-radius: 0;
    font-size: 13px; font-weight: 500;
    padding: 8px 14px; min-height: 34px;
}}
QPushButton#tab_btn:hover {{ color: {t['text_1']}; background: {tint1}; }}
QPushButton#tab_icon_btn {{
    background: transparent; color: {t['text_3']};
    border: 1px solid transparent; border-radius: 6px; font-size: 15px;
    min-width: 28px; max-width: 28px;
    min-height: 28px; max-height: 28px; padding: 0;
}}
QPushButton#tab_icon_btn:hover {{
    background: {t['surface_2']}; color: {t['text_1']}; border-color: {t['border']};
}}

/* ── Status bar ─────────────────────────── */
QWidget#status_bar {{
    background-color: {t['bg_statusbar']};
    border-top: 1px solid {t['hairline']};
}}
QLabel#status_bar_text {{
    color: {t['text_3']}; font-size: 11px;
    font-family: "Cascadia Mono", "Consolas", monospace;
    background: transparent;
}}
QLabel#status_bar_pill {{
    color: {t['text_2']}; font-size: 10px;
    font-family: "Cascadia Mono", "Consolas", monospace;
    background: {tint1}; border: 1px solid {t['hairline']};
    border-radius: 3px; padding: 1px 7px;
}}

/* ── Scroll ─────────────────────────────── */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{
    background: {scroll_thumb}; border-radius: 5px;
    min-height: 32px; margin: 2px;
}}
QScrollBar::handle:vertical:hover {{ background: {scroll_thumb_h}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

/* ── Buttons ─────────────────────────────── */
QPushButton {{
    background: {t['surface_2']}; color: {t['text_1']};
    border: 1px solid {t['border']}; border-radius: 6px;
    padding: 0 14px; font-weight: 500; font-size: 12px; min-height: 32px;
}}
QPushButton:hover {{ background: {t['surface_hover']}; border-color: {t['border_strong']}; }}
QPushButton:pressed {{ background: {t['surface_1']}; }}
QPushButton:disabled {{ background: {t['surface_1']}; color: {t['text_4']}; border-color: {t['hairline']}; }}

QPushButton#primary {{
    background: {t['accent']}; color: {t['on_accent']};
    border-color: {t['accent_deep']}; font-weight: 600;
}}
QPushButton#primary:hover {{ background: {t['accent_deep']}; }}

QPushButton#ghost {{ background: transparent; color: {t['text_2']}; border-color: transparent; }}
QPushButton#ghost:hover {{
    background: {t['surface_2']}; color: {t['text_1']}; border-color: {t['border']};
}}

QPushButton#danger_ghost {{ background: transparent; color: {t['danger']}; border-color: {dng30}; }}
QPushButton#danger_ghost:hover {{ background: {dng10}; border-color: {dng55}; }}

QPushButton#chip {{
    background: {t['surface_1']}; color: {t['text_2']};
    border: 1px solid {t['hairline']}; border-radius: 6px;
    padding: 0 10px; font-size: 12px; min-height: 32px;
}}
QPushButton#chip:hover {{ border-color: {t['border_strong']}; color: {t['text_1']}; }}

QPushButton#theme_active {{
    background: {t['accent']}; color: {t['on_accent']};
    border: 1px solid {t['accent_deep']}; border-radius: 6px;
    padding: 0 16px; font-weight: 600; font-size: 12px; min-height: 32px;
}}
QPushButton#theme_inactive {{
    background: {t['surface_2']}; color: {t['text_2']};
    border: 1px solid {t['border']}; border-radius: 6px;
    padding: 0 16px; font-size: 12px; min-height: 32px;
}}
QPushButton#theme_inactive:hover {{
    background: {t['surface_hover']}; color: {t['text_1']}; border-color: {t['border_strong']};
}}

QPushButton#hotkey_btn {{
    background: {acc10}; color: {t['text_1']};
    border: 1px solid {acc35}; border-radius: 8px;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-weight: 600; font-size: 12px;
    padding: 6px 14px; min-height: 36px; min-width: 160px;
}}
QPushButton#hotkey_btn:hover {{ background: {acc18}; border-color: {acc50}; }}

/* ── Inputs ──────────────────────────────── */
QLineEdit {{
    border: 1px solid {t['border']}; border-radius: 6px;
    padding: 0 11px; background: {t['surface_2']}; color: {t['text_1']};
    font-size: 12px; font-family: "Cascadia Mono", "Consolas", monospace;
    min-height: 32px;
    selection-background-color: {acc35}; selection-color: {t['text_1']};
}}
QLineEdit:focus {{ border-color: {t['accent_deep']}; background: {t['surface_1']}; }}
QLineEdit:disabled {{ background: {t['surface_1']}; color: {t['text_4']}; border-color: {t['hairline']}; }}
QLineEdit#search_input {{
    background: {t['surface_1']}; border-color: {t['hairline']};
    font-family: "Segoe UI Variable", "Segoe UI", sans-serif;
    padding-left: 32px;
}}
QLineEdit#search_input:focus {{ border-color: {t['accent_deep']}; }}

/* ── ComboBox ────────────────────────────── */
QComboBox {{
    border: 1px solid {t['border']}; border-radius: 6px;
    padding: 0 10px; background: {t['surface_2']}; color: {t['text_1']};
    font-size: 12px; min-height: 32px;
}}
QComboBox:focus {{ border-color: {t['accent_deep']}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    border: 1px solid {t['border']}; border-radius: 4px;
    background: {t['surface_2']}; selection-background-color: {acc10};
    selection-color: {t['text_1']}; color: {t['text_1']};
    outline: none; padding: 4px;
}}
QComboBox:disabled {{ background: {t['surface_1']}; color: {t['text_4']}; }}

/* ── Labels ──────────────────────────────── */
QLabel#section_label {{
    color: {t['text_3']}; font-size: 10px; font-weight: 600;
    letter-spacing: 1.2px; background: transparent;
}}
QLabel#hint {{ color: {t['text_4']}; font-size: 11px; background: transparent; }}
QLabel#form_label {{ color: {t['text_2']}; font-size: 12px; font-weight: 500; background: transparent; }}
QLabel#meta_label {{
    color: {t['text_4']}; font-size: 11px;
    font-family: "Cascadia Mono", "Consolas", monospace; background: transparent;
}}
QLabel#card_date {{
    color: {t['text_3']}; font-size: 11px;
    font-family: "Cascadia Mono", "Consolas", monospace; background: transparent;
}}
QLabel#card_duration {{
    color: {t['text_2']}; font-size: 10px;
    font-family: "Cascadia Mono", "Consolas", monospace;
    background: {tint1}; border: 1px solid {t['hairline']};
    border-radius: 3px; padding: 1px 6px;
}}
QLabel#card_body {{ color: {t['text_1']}; font-size: 13px; background: transparent; }}
QLabel#stat_label {{
    color: {t['text_3']}; font-size: 10px; font-weight: 600;
    letter-spacing: 1px; background: transparent;
}}
QLabel#stat_value {{
    color: {t['text_1']}; font-size: 22px; font-weight: 600;
    font-family: "Cascadia Mono", "Consolas", monospace;
    background: transparent; letter-spacing: -1px;
}}
QLabel#stat_unit {{
    color: {t['text_3']}; font-size: 10px;
    font-family: "Cascadia Mono", "Consolas", monospace; background: transparent;
}}
QLabel#greeting {{
    color: {t['text_1']}; font-size: 18px; font-weight: 600; background: transparent;
}}

/* ── App frame (shadow host) ─────────────── */
QFrame#app_frame {{
    background-color: {t['bg_app']};
    border: 1px solid rgba(0,0,0,102);
}}

/* ── Frames / Cards ──────────────────────── */
QFrame#card {{
    background: {t['surface_1']}; border: 1px solid {t['hairline']}; border-radius: 12px;
}}
QFrame#stat_card {{
    background: {t['surface_1']}; border: 1px solid {t['hairline']}; border-radius: 10px;
}}
QFrame#transcript_card {{
    background: {t['surface_1']}; border: 1px solid {t['hairline']}; border-radius: 12px;
}}
QFrame#hotkey_frame {{
    background: {acc10}; border: 1px solid {acc35}; border-radius: 8px;
}}
QFrame#provider_card {{
    background: {t['surface_2']}; border: 1px solid {t['border']}; border-radius: 8px;
}}
QFrame#provider_card_active {{
    background: {t['surface_2']}; border: 2px solid {t['accent_deep']}; border-radius: 8px;
}}

/* ── Radio ───────────────────────────────── */
QRadioButton {{ font-size: 12px; spacing: 8px; color: {t['text_2']}; background: transparent; }}
QRadioButton::indicator {{
    width: 14px; height: 14px;
    border: 1.5px solid {t['text_4']}; border-radius: 7px; background: transparent;
}}
QRadioButton::indicator:checked {{ background: {t['accent']}; border-color: {t['accent']}; }}

/* ── Group Box ───────────────────────────── */
QGroupBox {{
    border: none; border-top: 1px solid {t['hairline']};
    margin-top: 20px; padding-top: 16px;
    font-size: 10px; font-weight: 600; color: {t['text_3']};
    letter-spacing: 1.2px; background: transparent;
}}
QGroupBox::title {{
    subcontrol-origin: margin; subcontrol-position: top left;
    padding: 0 6px; background: {t['bg_app']};
    color: {t['text_3']}; font-size: 10px; font-weight: 600;
}}

/* ── Misc ────────────────────────────────── */
QMessageBox {{ background: {t['surface_1']}; }}
QToolTip {{
    background: {t['surface_1']}; color: {t['text_1']};
    border: 1px solid {t['border']}; border-radius: 6px;
    padding: 5px 10px; font-size: 12px;
}}
"""


def build_overlay_stylesheet(theme: str = "dark") -> str:
    t = TOKENS.get(theme, DARK)
    return f"""
QLabel#overlay_text {{
    color: {t['text_1']}; font-weight: 600; font-size: 13px;
    font-family: "Segoe UI Variable", "Segoe UI", sans-serif; background: transparent;
}}
QLabel#overlay_timer {{
    color: {t['accent']}; font-weight: 600; font-size: 12px;
    font-family: "Cascadia Mono", "Consolas", monospace; background: transparent;
}}
"""
