# Only ever selected on darwin, but macOS-only modules are imported inside the functions
# (ApplicationServices and IOKit are loaded via ctypes, fcntl and AppKit via import) so this file still
# imports and can be tested on Windows.
import logging
import os
import plistlib
import subprocess
import sys
import time
from pathlib import Path

_log = logging.getLogger(__name__)

BUNDLE_ID = "com.mta.voiceflow"
DATA_DIR_DISPLAY = "~/Library/Application Support/VoiceFlow"
# NSPasteboard writes are not guaranteed to be visible to the frontmost app by the time
# the synthetic Cmd+V arrives.
PASTE_DELAY_S = 0.05

ACCESSIBILITY_PANE = "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
INPUT_MONITORING_PANE = "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"
_APP_SERVICES = "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
_IOKIT = "/System/Library/Frameworks/IOKit.framework/IOKit"
_IOHID_REQUEST_TYPE_LISTEN_EVENT = 1
_IOHID_ACCESS_TYPE_GRANTED = 0
_RESTORE_WAIT_S = 0.15
_RESTORE_POLL_S = 0.01

_target_app = None


def prepare_qt_env() -> None:
    # Qt's QCocoaWindow::raise() also calls [NSApp activateIgnoringOtherApps:YES] unless this
    # is 0. That activates the whole menu-bar app (main window included) over the app the
    # user is dictating into, so Cmd+V would land in VoiceFlow.
    os.environ.setdefault("QT_MAC_SET_RAISE_PROCESS", "0")


def data_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / "VoiceFlow"


def _message_box():
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QMessageBox

    box = QMessageBox()
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle("VoiceFlow")
    # A menu-bar-only app is never the active app at startup, so without this the box
    # can open behind whatever window the user is in.
    box.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
    return box


def ensure_single_instance():
    import fcntl

    lock_dir = data_dir()
    lock_dir.mkdir(parents=True, exist_ok=True)
    # The kernel drops a flock when the process dies, so a crash never leaves a stale
    # lock behind. The fd is a plain int, so nothing closes it before the process exits.
    fd = os.open(lock_dir / "voiceflow.lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        from PyQt6.QtWidgets import QApplication

        _app = QApplication.instance() or QApplication(sys.argv)
        box = _message_box()
        box.setText("VoiceFlow is already running.\nCheck the menu bar.")
        box.exec()
        sys.exit(0)
    return fd


def _launch_agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{BUNDLE_ID}.plist"


def launch_agent_plist(exe: str) -> dict:
    return {"Label": BUNDLE_ID, "ProgramArguments": [exe], "RunAtLoad": True}


def autostart_is_enabled() -> bool:
    return _launch_agent_path().exists()


def autostart_enable(exe: str) -> bool:
    # Gatekeeper runs a quarantined app that was not moved out of Downloads from a
    # random read-only copy that disappears after quit; a login item pointing there
    # would silently never start.
    if "/AppTranslocation/" in exe:
        return False
    path = _launch_agent_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            plistlib.dump(launch_agent_plist(exe), f)
        return True
    except OSError:
        return False


def autostart_disable() -> bool:
    try:
        _launch_agent_path().unlink(missing_ok=True)
        return True
    except OSError:
        return False


def open_folder(path) -> None:
    subprocess.run(["open", str(path)], check=False)


def paste_modifier():
    from pynput.keyboard import Key
    return Key.cmd


def remember_target_app() -> None:
    global _target_app
    _target_app = None
    try:
        from AppKit import NSWorkspace

        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is not None and app.processIdentifier() != os.getpid():
            _target_app = app
    except Exception as e:
        _log.info("Could not read the frontmost app before recording: %s", e)


def restore_target_app() -> None:
    target = _target_app
    if target is None:
        return
    try:
        from AppKit import NSApplication, NSApplicationActivateIgnoringOtherApps, NSWorkspace

        workspace = NSWorkspace.sharedWorkspace()
        front = workspace.frontmostApplication()
        # Only undo VoiceFlow taking the front; an app the user switched to on purpose
        # while the text was processing keeps the paste, as on Windows.
        if target.isTerminated() or (front is not None and front.processIdentifier() != os.getpid()):
            return
        _log.info(
            "Re-activating %s before paste (frontmost was %s)",
            target.localizedName(), "VoiceFlow" if front is not None else "none",
        )
        app = NSApplication.sharedApplication()
        if app.respondsToSelector_("yieldActivationToApplication:"):
            app.yieldActivationToApplication_(target)
        target.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
        # frontmostApplication may only refresh on the next run-loop turn, so this can run
        # out: it then is just a bounded pause that lets the activation land before Cmd+V.
        deadline = time.monotonic() + _RESTORE_WAIT_S
        while time.monotonic() < deadline:
            time.sleep(_RESTORE_POLL_S)
            front = workspace.frontmostApplication()
            if front is not None and front.processIdentifier() == target.processIdentifier():
                return
    except Exception as e:
        _log.info("Could not re-activate the target app before paste: %s", e)


def bring_app_to_front() -> None:
    # QT_MAC_SET_RAISE_PROCESS=0 stops raise() from activating the app, so a window the user
    # explicitly asked for would open without keyboard focus.
    try:
        from AppKit import NSApplication

        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
    except Exception as e:
        _log.info("Could not activate VoiceFlow: %s", e)


def apply_window_shadow(win_id: int) -> None:
    pass


def check_accessibility() -> bool:
    import ctypes

    try:
        lib = ctypes.cdll.LoadLibrary(_APP_SERVICES)
        fn = lib.AXIsProcessTrusted
        fn.restype = ctypes.c_bool
        fn.argtypes = []
        return bool(fn())
    except Exception as e:
        # Can't ask the system: better no warning than a false one on every start.
        _log.info("Could not check Accessibility (AXIsProcessTrusted), assuming granted: %s", e)
        return True


def check_input_monitoring() -> bool:
    import ctypes

    try:
        lib = ctypes.cdll.LoadLibrary(_IOKIT)
        fn = lib.IOHIDCheckAccess
        fn.restype = ctypes.c_int32
        fn.argtypes = [ctypes.c_int32]
        return fn(_IOHID_REQUEST_TYPE_LISTEN_EVENT) == _IOHID_ACCESS_TYPE_GRANTED
    except Exception as e:
        _log.info("Could not check Input Monitoring (IOHIDCheckAccess), assuming granted: %s", e)
        return True


def open_privacy_pane(pane_url: str) -> None:
    subprocess.run(["open", pane_url], check=False)


def _prompt_accessibility_trust() -> None:
    # AXIsProcessTrusted only reads the current status; AXIsProcessTrustedWithOptions with
    # kAXTrustedCheckOptionPrompt=True additionally makes macOS show its own prompt and add
    # VoiceFlow to the Accessibility list (unchecked) the first time it runs.
    import ctypes

    try:
        cf = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
        )
        ax = ctypes.cdll.LoadLibrary(_APP_SERVICES)

        class _CFDictionaryKeyCallBacks(ctypes.Structure):
            _fields_ = [
                ("version", ctypes.c_long),
                ("retain", ctypes.c_void_p),
                ("release", ctypes.c_void_p),
                ("copyDescription", ctypes.c_void_p),
                ("equal", ctypes.c_void_p),
                ("hash", ctypes.c_void_p),
            ]

        class _CFDictionaryValueCallBacks(ctypes.Structure):
            _fields_ = [
                ("version", ctypes.c_long),
                ("retain", ctypes.c_void_p),
                ("release", ctypes.c_void_p),
                ("copyDescription", ctypes.c_void_p),
                ("equal", ctypes.c_void_p),
            ]

        key_callbacks = _CFDictionaryKeyCallBacks.in_dll(cf, "kCFTypeDictionaryKeyCallBacks")
        value_callbacks = _CFDictionaryValueCallBacks.in_dll(cf, "kCFTypeDictionaryValueCallBacks")
        prompt_key = ctypes.c_void_p.in_dll(ax, "kAXTrustedCheckOptionPrompt")
        true_value = ctypes.c_void_p.in_dll(cf, "kCFBooleanTrue")

        keys = (ctypes.c_void_p * 1)(prompt_key)
        values = (ctypes.c_void_p * 1)(true_value)

        cf.CFDictionaryCreate.restype = ctypes.c_void_p
        cf.CFDictionaryCreate.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long,
            ctypes.c_void_p, ctypes.c_void_p,
        ]
        options = cf.CFDictionaryCreate(
            None, keys, values, 1, ctypes.byref(key_callbacks), ctypes.byref(value_callbacks),
        )

        ax.AXIsProcessTrustedWithOptions.restype = ctypes.c_bool
        ax.AXIsProcessTrustedWithOptions.argtypes = [ctypes.c_void_p]
        ax.AXIsProcessTrustedWithOptions(options)

        if options:
            cf.CFRelease.argtypes = [ctypes.c_void_p]
            cf.CFRelease(options)
    except Exception as e:
        # Can't show the native prompt: fall back to the plain check further down, no dialog lost.
        _log.info(
            "Could not prompt for Accessibility trust (AXIsProcessTrustedWithOptions): %s", e
        )


def show_startup_permission_hint() -> None:
    if not check_accessibility():
        _prompt_accessibility_trust()
    missing = []
    if not check_accessibility():
        missing.append(("Accessibility", ACCESSIBILITY_PANE))
    if not check_input_monitoring():
        missing.append(("Input Monitoring", INPUT_MONITORING_PANE))
    if not missing:
        return
    from PyQt6.QtWidgets import QMessageBox

    names = " and ".join(name for name, _ in missing)
    box = _message_box()
    box.setText(f"VoiceFlow needs {names} permission to use the hotkey and paste text.")
    box.setInformativeText(
        f"In System Settings > Privacy & Security, turn VoiceFlow on under {names}. "
        "Then quit VoiceFlow from the menu bar and open it again.\n\n"
        "If VoiceFlow is not in the list, click + and choose VoiceFlow from Applications. "
        "If it is already switched on but the hotkey does not work (for example after "
        "installing a new version), select it, click -, then add it again with +."
    )
    first_name, first_pane = missing[0]
    open_btn = box.addButton(f"Open {first_name} Settings", QMessageBox.ButtonRole.AcceptRole)
    box.addButton("Later", QMessageBox.ButtonRole.RejectRole)
    box.exec()
    if box.clickedButton() is open_btn:
        open_privacy_pane(first_pane)
