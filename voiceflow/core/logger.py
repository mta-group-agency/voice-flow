import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from voiceflow.platform import data_dir

_MAX_BYTES = 1_000_000
_BACKUP_COUNT = 3
_FALLBACK_LOG_NAME = re.compile(r"voiceflow-\d+\.log(?:\.\d+)?")

_SECRET_PATTERNS = [
    (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), "AIza***"),
    (re.compile(r"gsk_[0-9A-Za-z]{20,}"), "gsk_***"),
    (re.compile(r"sk-ant-[0-9A-Za-z_\-]{20,}"), "sk-ant-***"),
    # Turso auth tokens are JWTs: header.payload.signature, each part base64url.
    # The lookbehind lets a match start only where a token run begins, so input like
    # "eyJeyJeyJ..." costs linear time instead of quadratic; it sits after the literal
    # so the engine can still jump straight to each "eyJ".
    (re.compile(r"eyJ(?<![0-9A-Za-z_\-]eyJ)[0-9A-Za-z_\-]+\.[0-9A-Za-z_\-]+\.[0-9A-Za-z_\-]+"), "eyJ***"),
    # Runs after the provider-specific patterns above; the lookahead keeps it from
    # re-swallowing a value they already masked (e.g. "key=AIza***" -> "key=***").
    (re.compile(r"key=(?!AIza\*\*\*|gsk_\*\*\*|sk-ant-\*\*\*|eyJ\*\*\*)[^&\s\"']+"), "key=***"),
]

_RECORD_START = r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3} \["
# Older versions logged everything at DEBUG, where HTTP client libraries dump whole
# requests (anthropic's "Request options" holds the dictated text, clipboard context and
# system prompt). Such a record goes together with its continuation lines (tracebacks);
# the final newline of the file is left in place so appended records start on a new line.
_LEGACY_HTTP_DEBUG = re.compile(
    rf"\n{_RECORD_START}DEBUG\] (?:anthropic|httpx|httpcore|urllib3|requests)(?:\.[\w.]+)?: [^\n]*"
    rf"(?:\n(?!{_RECORD_START}|\Z)[^\n]*)*"
)


def redact(text: str) -> str:
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class _RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


def _scrub_file(path: Path) -> None:
    original = path.read_text(encoding="utf-8", errors="replace")
    # The pattern starts with a literal "\n" (hence the prepended one) so the regex engine
    # skips from line to line instead of probing every character of a tens-of-MB file.
    scrubbed = redact(_LEGACY_HTTP_DEBUG.sub("", "\n" + original)[1:])
    if scrubbed != original:
        path.write_text(scrubbed, encoding="utf-8")


def _scrub_existing_logs(log_file: Path, used_file: Path) -> None:
    candidates = [used_file] + [Path(f"{used_file}.{i}") for i in range(1, _BACKUP_COUNT + 1)]
    if used_file == log_file:
        # Per-pid files left by earlier runs that could not open voiceflow.log. Rescrubbing
        # them is lossless; deleting them would drop the only trace of why that run fell back.
        candidates += sorted(
            p for p in log_file.parent.glob("voiceflow-*.log*") if _FALLBACK_LOG_NAME.fullmatch(p.name)
        )
    for path in candidates:
        if not path.exists():
            continue
        try:
            _scrub_file(path)
        except OSError as e:
            logging.getLogger("logger").warning("Could not scrub log file %s: %s", path, e)


def _make_handler(log_file: Path) -> tuple[logging.Handler, Path | None]:
    # voiceflow.log can be held open exclusively by another VoiceFlow instance
    # (or AV/backup software); fall back to a per-pid sibling rather than
    # crash on startup, and to NullHandler if even that can't be opened.
    for candidate in (log_file, log_file.with_name(f"voiceflow-{os.getpid()}.log")):
        try:
            handler = RotatingFileHandler(
                candidate, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
            )
        except OSError:
            continue
        handler.setFormatter(_RedactingFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        return handler, candidate
    return logging.NullHandler(), None


def setup() -> Path | None:
    log_dir = data_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "voiceflow.log"

    handler, used_file = _make_handler(log_file)
    handlers = [handler]
    if sys.stderr is not None and sys.stderr.isatty():
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(_RedactingFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        handlers.append(stream_handler)

    logging.basicConfig(level=logging.DEBUG, handlers=handlers)
    for noisy in ("urllib3", "httpx", "httpcore", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    def excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logging.getLogger("uncaught").critical(
            "Unhandled exception", exc_info=(exc_type, exc_value, exc_tb)
        )

    sys.excepthook = excepthook

    if used_file is not None:
        _scrub_existing_logs(log_file, used_file)

    return used_file


def get(name: str) -> logging.Logger:
    return logging.getLogger(name)
