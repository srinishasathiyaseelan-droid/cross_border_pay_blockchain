"""Tamper-evident audit chain in SQLite (M4, H2).

Adapted from Netvrio (sandysunny99/razorpay-ai-risk-manager @98bbc09) backend/audit/audit_log.py — sqlite3
instead of SQLAlchemy; HMAC-SHA256 keyed with LEDGER_SIGNING_KEY instead of an unkeyed SHA-256 (anyone with DB
write access could recompute a bare hash chain); append() runs inside the caller's DB transaction so a decision,
its block and its audit record commit or roll back together. The UNIQUE(previous_hash) fork guard is kept.
"""
import hashlib
import hmac
import json
import secrets
import threading

from ..db import utcnow_iso

GENESIS = "GENESIS"


def canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def chain_hash(key: bytes, payload: dict, prev_hash: str) -> str:
    return hmac.new(key, (prev_hash + canonical(payload)).encode("utf-8"), hashlib.sha256).hexdigest()


class AuditChain:
    def __init__(self, signing_key: str):
        if not signing_key:
            raise ValueError("LEDGER_SIGNING_KEY is required")
        self.key = signing_key.encode("utf-8")
        self._lock = threading.Lock()
        self._verified_id = 0
        self._verified_hash = GENESIS
        self._broken = False

    def append(self, conn, record_type: str, tx_id: str, payload: dict) -> dict:
        """Append inside an open transaction (BEGIN IMMEDIATE holds the write lock, so the tail cannot move)."""
        if not conn.in_transaction:
            raise RuntimeError("AuditChain.append must run inside a database transaction")
        row = conn.execute("SELECT current_hash FROM audit_chain ORDER BY id DESC LIMIT 1").fetchone()
        prev = row[0] if row else GENESIS
        record = {"record_type": record_type, "tx_id": tx_id, "payload": payload}
        current = chain_hash(self.key, record, prev)
        record_id = "AR-" + secrets.token_hex(8)
        conn.execute(
            """INSERT INTO audit_chain (record_id, tx_id, record_type, payload, previous_hash, current_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (record_id, tx_id, record_type, canonical(payload), prev, current, utcnow_iso()),
        )
        return {"record_id": record_id, "previous_hash": prev, "current_hash": current}

    def _check(self, rows, expected_prev):
        for r in rows:
            record = {"record_type": r["record_type"], "tx_id": r["tx_id"], "payload": json.loads(r["payload"])}
            if r["previous_hash"] != expected_prev:
                return False, f"Audit record {r['id']} ({r['tx_id']}) is not linked to the previous record", expected_prev
            if not hmac.compare_digest(chain_hash(self.key, record, expected_prev), r["current_hash"]):
                return False, f"Audit record {r['id']} ({r['tx_id']}) fails its HMAC signature check", expected_prev
            expected_prev = r["current_hash"]
        return True, "ok", expected_prev

    def verify(self, conn):
        rows = conn.execute("SELECT * FROM audit_chain ORDER BY id ASC").fetchall()
        ok, msg, _ = self._check(rows, GENESIS)
        if not ok:
            return False, msg, len(rows)
        return True, f"All {len(rows)} audit records carry valid HMAC-SHA256 links.", len(rows)

    def verify_incremental(self, conn) -> bool:
        """Only rows appended since the last call; a full verify() also catches edits to old rows."""
        with self._lock:
            if self._broken:
                return False
            rows = conn.execute("SELECT * FROM audit_chain WHERE id > ? ORDER BY id ASC",
                                (self._verified_id,)).fetchall()
            ok, _msg, tail = self._check(rows, self._verified_hash)
            if not ok:
                self._broken = True
                return False
            if rows:
                self._verified_id, self._verified_hash = rows[-1]["id"], tail
            return True

    @staticmethod
    def records(conn, record_types=None):
        sql = "SELECT * FROM audit_chain"
        params = []
        if record_types:
            sql += " WHERE record_type IN (%s)" % ",".join("?" * len(record_types))
            params = list(record_types)
        return conn.execute(sql + " ORDER BY id ASC", params).fetchall()
