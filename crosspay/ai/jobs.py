"""Background AI jobs so the payment response stays fast (LLM06).

ThreadPoolExecutor(max_workers=2) + an ai_jobs table (task, tx_id, status, result). At most QUEUE_CAP jobs may be
pending; extra jobs are recorded as QUEUE_FULL and dropped. Tests (AI_RUN_SYNC) run jobs inline.
"""
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from ..db import connect, utcnow_iso

log = logging.getLogger(__name__)
QUEUE_CAP = 50


class JobRunner:
    def __init__(self, app, max_workers: int = 2):
        self.app = app
        self.pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="crosspay-ai")
        self._pending = 0
        self._lock = threading.Lock()

    def submit(self, conn, task: str, tx_id: str, fn) -> str:
        """fn(conn) -> GuardedResult. Returns the job status right after submission."""
        existing = conn.execute("SELECT status FROM ai_jobs WHERE task = ? AND tx_id = ?", (task, tx_id)).fetchone()
        if existing and existing[0] in ("PENDING", "DONE"):
            return existing[0]
        with self._lock:
            if self._pending >= QUEUE_CAP:
                _upsert(conn, task, tx_id, "QUEUE_FULL", None, "QUEUE_FULL")
                return "QUEUE_FULL"
            self._pending += 1
        _upsert(conn, task, tx_id, "PENDING", None, None)
        if self.app.config.get("AI_RUN_SYNC"):
            self._run(task, tx_id, fn)
        else:
            self.pool.submit(self._run, task, tx_id, fn)
        return conn.execute("SELECT status FROM ai_jobs WHERE task = ? AND tx_id = ?", (task, tx_id)).fetchone()[0]

    def _run(self, task, tx_id, fn):
        conn = connect(self.app.config["DB_PATH"])
        try:
            with self.app.app_context():
                result = fn(conn)
            status = "DONE" if result.ok else ("UNAVAILABLE" if result.status in ("UNAVAILABLE", "DISABLED") else "FAILED")
            _upsert(conn, task, tx_id, status, result.data if result.ok else None, None if result.ok else result.status)
        except Exception:  # noqa: BLE001
            log.exception("AI job %s/%s failed", task, tx_id)
            _upsert(conn, task, tx_id, "FAILED", None, "EXCEPTION")
        finally:
            conn.close()
            with self._lock:
                self._pending -= 1


def _upsert(conn, task, tx_id, status, result, error_code):
    now = utcnow_iso()
    conn.execute(
        """INSERT INTO ai_jobs (task, tx_id, status, result_json, error_code, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(task, tx_id) DO UPDATE SET status = excluded.status, result_json = excluded.result_json,
               error_code = excluded.error_code, updated_at = excluded.updated_at""",
        (task, tx_id, status, json.dumps(result) if result is not None else None, error_code, now, now),
    )


def get(conn, task: str, tx_id: str):
    row = conn.execute("SELECT status, result_json, error_code FROM ai_jobs WHERE task = ? AND tx_id = ?",
                       (task, tx_id)).fetchone()
    if not row:
        return None
    return {"status": row[0], "result": json.loads(row[1]) if row[1] else None, "error_code": row[2]}
