"""Double-submit protection (H2).

Adapted from Netvrio (sandysunny99/razorpay-ai-risk-manager @98bbc09) backend/security/idempotency.py — a
UNIQUE (user_id, key) row in SQLite instead of Redis, claimed inside the payment's DB transaction, so a
double-submitted form can never mine two blocks.
"""
import sqlite3
import uuid

from ..db import utcnow_iso


def new_key() -> str:
    return uuid.uuid4().hex


def claim(conn, user_id: int, key: str):
    """Returns None when the key is new (and claims it), else the tx_id already created with it."""
    try:
        conn.execute("INSERT INTO idempotency_keys (user_id, key, created_at) VALUES (?, ?, ?)",
                     (user_id, key, utcnow_iso()))
        return None
    except sqlite3.IntegrityError:
        row = conn.execute("SELECT tx_id FROM idempotency_keys WHERE user_id = ? AND key = ?",
                           (user_id, key)).fetchone()
        return row[0] if row and row[0] else "IN_PROGRESS"


def bind(conn, user_id: int, key: str, tx_id: str) -> None:
    conn.execute("UPDATE idempotency_keys SET tx_id = ? WHERE user_id = ? AND key = ?", (tx_id, user_id, key))
