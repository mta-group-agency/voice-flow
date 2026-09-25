"""The only place with per-OS differences; the rest of the app imports from here."""
import sys

IS_MAC = sys.platform == "darwin"

if IS_MAC:
    from voiceflow.platform.macos import (
        DATA_DIR_DISPLAY, PASTE_DELAY_S, apply_window_shadow, autostart_disable,
        autostart_enable, autostart_is_enabled, data_dir, ensure_single_instance,
        open_folder, paste_modifier, show_startup_permission_hint,
    )
else:
    from voiceflow.platform.windows import (
        DATA_DIR_DISPLAY, PASTE_DELAY_S, apply_window_shadow, autostart_disable,
        autostart_enable, autostart_is_enabled, data_dir, ensure_single_instance,
        open_folder, paste_modifier, show_startup_permission_hint,
    )

__all__ = [
    "IS_MAC", "DATA_DIR_DISPLAY", "PASTE_DELAY_S", "apply_window_shadow", "autostart_disable",
    "autostart_enable", "autostart_is_enabled", "data_dir", "ensure_single_instance",
    "open_folder", "paste_modifier", "show_startup_permission_hint",
]
