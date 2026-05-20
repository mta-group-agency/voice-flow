"""
Turso (libSQL) storage via HTTP API.
Falls back gracefully when URL/token are not configured.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import requests


@dataclass
class TranscriptionEntry:
    raw_text: str
    final_text: str
    duration_s: float
    audio_s: float
    char_count: int
    ai_provider: str
    cost_usd: float = 0.0
    created_at: Optional[str] = None


@dataclass
class MonthStats:
    year: int
    month: int
    sessions: int
    total_chars: int
    total_audio_s: float
    cost_usd: float
    ai_provider: str


_CREATE_TRANSCRIPTIONS = """
CREATE TABLE IF NOT EXISTS transcriptions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  raw_text    TEXT NOT NULL,
  final_text  TEXT NOT NULL,
  duration_s  REAL,
  audio_s     REAL,
  char_count  INTEGER
)
"""

_CREATE_MONTHLY_STATS = """
CREATE TABLE IF NOT EXISTS monthly_stats (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  year            INTEGER NOT NULL,
  month           INTEGER NOT NULL,
  sessions        INTEGER DEFAULT 0,
  total_chars     INTEGER DEFAULT 0,
  total_audio_s   REAL DEFAULT 0,
  cost_usd        REAL DEFAULT 0,
  ai_provider     TEXT,
  UNIQUE(year, month, ai_provider)
)
"""


class HistoryDB:
    def __init__(self, db_url: str = "", auth_token: str = ""):
        self._url = db_url.rstrip("/") if db_url else ""
        self._token = auth_token
        self._enabled = bool(self._url and self._token)
        if self._enabled:
            self._http_url = self._url.replace("libsql://", "https://")
            self._ensure_schema()

    def _enabled_check(self) -> bool:
        return self._enabled

    def reconfigure(self, db_url: str, auth_token: str):
        self._url = db_url.rstrip("/") if db_url else ""
        self._token = auth_token
        self._enabled = bool(self._url and self._token)
        if self._enabled:
            self._http_url = self._url.replace("libsql://", "https://")
            self._ensure_schema()

    def _execute(self, statements: list[dict]) -> list[dict]:
        requests_payload = [{"type": "execute", "stmt": s} for s in statements]
        requests_payload.append({"type": "close"})
        resp = requests.post(
            f"{self._http_url}/v2/pipeline",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
            json={"requests": requests_payload},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for r in data.get("results", []):
            if r.get("type") == "ok":
                response = r.get("response", {})
                if response.get("type") == "execute":
                    results.append(response.get("result", {}))
        return results

    def _stmt(self, sql: str, args: list | None = None) -> dict:
        stmt: dict = {"sql": sql}
        if args:
            stmt["args"] = [self._to_value(a) for a in args]
        return stmt

    def _to_value(self, v):
        if v is None:
            return {"type": "null"}
        if isinstance(v, int):
            return {"type": "integer", "value": str(v)}
        if isinstance(v, float):
            return {"type": "float", "value": v}
        return {"type": "text", "value": str(v)}

    def _ensure_schema(self):
        try:
            self._execute([
                self._stmt(_CREATE_TRANSCRIPTIONS),
                self._stmt(_CREATE_MONTHLY_STATS),
            ])
        except Exception:
            pass
        self._backfill_costs()

    def _backfill_costs(self):
        # One-time fix: rows stored before cost tracking was added have cost_usd=0.
        # Re-estimate using the same formula as GeminiClient.estimate_cost.
        try:
            self._execute([
                self._stmt(
                    """
                    UPDATE monthly_stats
                    SET cost_usd = (total_audio_s * 25.0 / 1000000.0)
                                 + (total_chars / 4.0 * 3.5 / 1000000.0)
                    WHERE cost_usd = 0 AND sessions > 0
                    """
                )
            ])
        except Exception:
            pass

    def insert(self, entry: TranscriptionEntry) -> bool:
        if not self._enabled:
            return False
        now = datetime.now()
        try:
            self._execute([
                self._stmt(
                    "INSERT INTO transcriptions (raw_text, final_text, duration_s, audio_s, char_count) "
                    "VALUES (?, ?, ?, ?, ?)",
                    [entry.raw_text, entry.final_text, entry.duration_s, entry.audio_s, entry.char_count],
                ),
                self._stmt(
                    """
                    INSERT INTO monthly_stats (year, month, sessions, total_chars, total_audio_s, cost_usd, ai_provider)
                    VALUES (?, ?, 1, ?, ?, ?, ?)
                    ON CONFLICT(year, month, ai_provider) DO UPDATE SET
                      sessions = sessions + 1,
                      total_chars = total_chars + excluded.total_chars,
                      total_audio_s = total_audio_s + excluded.total_audio_s,
                      cost_usd = cost_usd + excluded.cost_usd
                    """,
                    [now.year, now.month, entry.char_count, entry.audio_s, entry.cost_usd, entry.ai_provider],
                ),
            ])
            return True
        except Exception:
            return False

    def get_recent(self, limit: int = 10) -> list[dict]:
        if not self._enabled:
            return []
        try:
            results = self._execute([
                self._stmt(
                    "SELECT id, created_at, raw_text, final_text, duration_s FROM transcriptions "
                    "ORDER BY id DESC LIMIT ?",
                    [limit],
                )
            ])
            if not results:
                return []
            result = results[0]
            cols = [c["name"] for c in result.get("cols", [])]
            rows = []
            for row in result.get("rows", []):
                rows.append({cols[i]: (v.get("value") if isinstance(v, dict) else v) for i, v in enumerate(row)})
            return rows
        except Exception:
            return []

    def get_stats(self, year: int, month: int) -> list[MonthStats]:
        if not self._enabled:
            return []
        try:
            results = self._execute([
                self._stmt(
                    "SELECT year, month, sessions, total_chars, total_audio_s, cost_usd, ai_provider "
                    "FROM monthly_stats WHERE year=? AND month=? ORDER BY ai_provider",
                    [year, month],
                )
            ])
            if not results:
                return []
            result = results[0]
            cols = [c["name"] for c in result.get("cols", [])]
            stats = []
            for row in result.get("rows", []):
                d = {cols[i]: (v.get("value") if isinstance(v, dict) else v) for i, v in enumerate(row)}
                stats.append(MonthStats(
                    year=int(d.get("year", year)),
                    month=int(d.get("month", month)),
                    sessions=int(d.get("sessions", 0)),
                    total_chars=int(d.get("total_chars", 0)),
                    total_audio_s=float(d.get("total_audio_s", 0)),
                    cost_usd=float(d.get("cost_usd", 0)),
                    ai_provider=str(d.get("ai_provider", "")),
                ))
            return stats
        except Exception:
            return []

    def get_daily_sessions(self, year: int, month: int) -> list[tuple[int, int]]:
        """Returns [(day, count), ...] sorted by day for the given month."""
        if not self._enabled:
            return []
        try:
            results = self._execute([
                self._stmt(
                    """
                    SELECT CAST(strftime('%d', created_at) AS INTEGER) AS day,
                           COUNT(*) AS cnt
                    FROM transcriptions
                    WHERE strftime('%Y', created_at) = ?
                      AND strftime('%m', created_at) = ?
                    GROUP BY day
                    ORDER BY day
                    """,
                    [str(year), f"{month:02d}"],
                )
            ])
            if not results:
                return []
            result = results[0]
            cols = [c["name"] for c in result.get("cols", [])]
            rows = []
            for row in result.get("rows", []):
                d = {cols[i]: (v.get("value") if isinstance(v, dict) else v) for i, v in enumerate(row)}
                rows.append((int(d["day"]), int(d["cnt"])))
            return rows
        except Exception:
            return []

    def get_available_months(self) -> list[tuple[int, int]]:
        if not self._enabled:
            return []
        try:
            results = self._execute([
                self._stmt(
                    "SELECT DISTINCT year, month FROM monthly_stats ORDER BY year DESC, month DESC"
                )
            ])
            if not results:
                return []
            result = results[0]
            cols = [c["name"] for c in result.get("cols", [])]
            months = []
            for row in result.get("rows", []):
                d = {cols[i]: (v.get("value") if isinstance(v, dict) else v) for i, v in enumerate(row)}
                months.append((int(d["year"]), int(d["month"])))
            return months
        except Exception:
            return []

    def clear_history(self) -> bool:
        if not self._enabled:
            return False
        try:
            self._execute([self._stmt("DELETE FROM transcriptions")])
            return True
        except Exception:
            return False

    @property
    def is_enabled(self) -> bool:
        return self._enabled
