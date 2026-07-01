"""
Auto-update against GitHub releases of mta-group-agency/voice-flow.

Checks the latest release, and (when running as a frozen one-file exe) downloads
and swaps the VoiceFlow.exe in place. Any failure falls back to opening the
release page in the browser — a failed update must never brick the install.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import requests

from voiceflow.__version__ import __version__
from voiceflow.core import logger

_LATEST_URL = "https://api.github.com/repos/mta-group-agency/voice-flow/releases/latest"
_TAG_URL = "https://api.github.com/repos/mta-group-agency/voice-flow/releases/tags/v{version}"
_ASSET_NAME = "VoiceFlow.exe"
_HEADERS = {"Accept": "application/vnd.github+json"}
_CHECK_TIMEOUT = 10
_DOWNLOAD_TIMEOUT = 300

_log = logger.get("updater")


@dataclass
class UpdateInfo:
    update_available: bool
    latest_version: str
    download_url: str
    html_url: str
    sha256: Optional[str]
    size: int
    body: str = ""
    video_url: Optional[str] = None


_VIDEO_LINE_PREFIXES = ("walkthrough:", "wideo:", "video:")
_URL_RE = re.compile(r"https?://[^\s)>\]]+")


def loom_gif_url(video_url: Optional[str]) -> Optional[str]:
    if not video_url or "loom.com" not in video_url:
        return None
    try:
        resp = requests.get(
            "https://www.loom.com/v1/oembed",
            params={"url": video_url},
            timeout=_CHECK_TIMEOUT,
        )
        resp.raise_for_status()
        thumb = resp.json().get("thumbnail_url")
        return thumb or None
    except (requests.RequestException, ValueError):
        return None


def fetch_release_notes(version: str) -> tuple[str, Optional[str]]:
    try:
        resp = requests.get(
            _TAG_URL.format(version=version), headers=_HEADERS, timeout=_CHECK_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        _log.debug("Release notes fetch failed: %s", type(e).__name__)
        return "", None

    body = data.get("body", "") or ""
    return body, _extract_video_url(body)


def _extract_video_url(body: str) -> Optional[str]:
    if not body:
        return None
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(_VIDEO_LINE_PREFIXES):
            match = _URL_RE.search(stripped)
            if match:
                return match.group(0)
    for match in _URL_RE.finditer(body):
        url = match.group(0)
        low = url.lower()
        if "loom.com" in low or "clickup" in low:
            return url
    return None


def _parse_semver(version: str) -> Optional[tuple[int, int, int]]:
    parts = version.strip().lstrip("v").split(".")
    if len(parts) != 3:
        return None
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None


def _is_newer(remote: str, local: str) -> bool:
    r, l = _parse_semver(remote), _parse_semver(local)
    if r is None or l is None:
        return False
    return r > l


def check_for_update() -> Optional[UpdateInfo]:
    try:
        resp = requests.get(_LATEST_URL, headers=_HEADERS, timeout=_CHECK_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        _log.debug("Update check failed: %s", type(e).__name__)
        return None

    latest_version = str(data.get("tag_name", "")).lstrip("v")
    html_url = data.get("html_url", "")

    asset = next(
        (a for a in data.get("assets", []) if a.get("name") == _ASSET_NAME),
        None,
    )
    if not latest_version or asset is None:
        _log.debug("Latest release has no usable %s asset", _ASSET_NAME)
        return None

    digest = asset.get("digest")
    sha256 = digest.split("sha256:", 1)[1] if digest and digest.startswith("sha256:") else None

    body = data.get("body", "") or ""

    return UpdateInfo(
        update_available=_is_newer(latest_version, __version__),
        latest_version=latest_version,
        download_url=asset.get("browser_download_url", ""),
        html_url=html_url,
        sha256=sha256,
        size=int(asset.get("size", 0)),
        body=body,
        video_url=_extract_video_url(body),
    )


def _download(url: str, dest: Path, progress: Optional[Callable[[int], None]]) -> None:
    with requests.get(url, stream=True, timeout=_DOWNLOAD_TIMEOUT) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if progress and total:
                    progress(int(downloaded * 100 / total))
    if progress:
        progress(100)


def _verify_sha256(path: Path, expected: str) -> bool:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().lower() == expected.lower()


def _spawn_swap_helper(old_path: Path, target_path: Path) -> None:
    helper = target_path.parent / "_vf_update.bat"
    pid = os.getpid()
    script = f"""@echo off
:waitloop
tasklist /FI "PID eq {pid}" 2>nul | find "{pid}" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto waitloop
)
start "" "{target_path}"
del "{old_path}"
del "%~f0"
"""
    helper.write_text(script, encoding="ascii")
    subprocess.Popen(
        ["cmd", "/c", str(helper)],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
        close_fds=True,
    )


def can_self_update() -> bool:
    if not getattr(sys, "frozen", False):
        return False
    return os.access(Path(sys.executable).parent, os.W_OK)


def apply_update(info: UpdateInfo, progress: Optional[Callable[[int], None]] = None) -> bool:
    """
    Download, verify and swap the running exe. Returns True if the swap helper was
    launched and the app should now quit; False if the caller should fall back to
    opening the release page. The config in %APPDATA% is never touched.
    """
    if not can_self_update():
        _log.debug("Self-update not possible (not frozen or no write access)")
        return False

    target = Path(sys.executable)
    tmp = target.parent / f"VoiceFlow-{info.latest_version}.exe.download"

    try:
        _download(info.download_url, tmp, progress)
    except requests.RequestException as e:
        _log.warning("Update download failed: %s", type(e).__name__)
        tmp.unlink(missing_ok=True)
        return False

    if info.sha256 and not _verify_sha256(tmp, info.sha256):
        _log.error("Update SHA256 mismatch, aborting swap")
        tmp.unlink(missing_ok=True)
        return False

    old = target.with_suffix(".old")
    try:
        old.unlink(missing_ok=True)
        target.rename(old)
        tmp.replace(target)
    except OSError as e:
        _log.error("Update swap failed: %s", e)
        if old.exists() and not target.exists():
            old.rename(target)
        tmp.unlink(missing_ok=True)
        return False

    _spawn_swap_helper(old, target)
    return True
