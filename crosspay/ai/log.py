"""llm_calls audit log, response cache and retention (G9, LLM06).

Only the DLP-redacted input and its hash are stored, never the raw prompt. Rows older than LLM_LOG_RETENTION_DAYS are
purged at startup and at most once a day afterwards.
"""
import json
import threading
from datetime import datetime, timedelta, timezone

from ..db import utcnow_iso

_last_purge = {"day": None}
_lock = threading.Lock()


def record(conn, *, task, prompt_version, provider, model, tx_id, user_id, input_hash, redacted_input, status,
           guard_outcome, output_json, latency_ms, input_tokens, output_tokens, cost_usd) -> None:
    conn.execute(
        """INSERT INTO llm_calls (task, prompt_version, provider, model, tx_id, user_id, input_hash, redacted_input,
               status, guard_outcome, output_json, latency_ms, input_tokens, output_tokens, cost_usd, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (task, prompt_version, provider, model, tx_id, user_id, input_hash, (redacted_input or "")[:8000], status,
         guard_outcome, json.dumps(output_json) if output_json is not None else None, latency_ms, input_tokens,
         output_tokens, round(cost_usd or 0.0, 6), utcnow_iso()),
    )


def cache_get(conn, task, prompt_version, input_hash):
    row = conn.execute("SELECT output_json FROM ai_cache WHERE task = ? AND prompt_version = ? AND input_hash = ?",
                       (task, prompt_version, input_hash)).fetchone()
    return json.loads(row[0]) if row else None


def cache_put(conn, task, prompt_version, input_hash, output) -> None:
    conn.execute("INSERT OR REPLACE INTO ai_cache (task, prompt_version, input_hash, output_json, created_at) "
                 "VALUES (?, ?, ?, ?, ?)", (task, prompt_version, input_hash, json.dumps(output), utcnow_iso()))


def purge(conn, retention_days: int, force: bool = False) -> int:
    today = datetime.now(timezone.utc).date().isoformat()
    with _lock:
        if not force and _last_purge["day"] == today:
            return 0
        _last_purge["day"] = today
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).replace(microsecond=0).isoformat()
    cutoff = cutoff.replace("+00:00", "Z")
    cur = conn.execute("DELETE FROM llm_calls WHERE created_at < ?", (cutoff,))
    conn.execute("DELETE FROM ai_cache WHERE created_at < ?", (cutoff,))
    return cur.rowcount or 0


def spend_today(conn) -> float:
    day = datetime.now(timezone.utc).date().isoformat()
    return float(conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM llm_calls WHERE created_at >= ?",
                              (day + "T00:00:00Z",)).fetchone()[0])
