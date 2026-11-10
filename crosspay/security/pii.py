"""PII handling (L6): government IDs are encrypted at rest (Fernet) and masked in the UI.

The key is KYC_ENCRYPTION_KEY if set, else derived from SECRET_KEY. Values that are not Fernet tokens
(legacy plaintext rows) are encrypted on startup by encrypt_legacy_rows().
"""
import base64
import hashlib
import re

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9.\-]{1,190}\.[A-Za-z]{2,24}$")
MIN_PASSWORD_LEN = 10


def _fernet(secret: str) -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(("crosspay-kyc:" + secret).encode()).digest())
    return Fernet(key)


def _app_fernet() -> Fernet:
    cfg = current_app.config
    return _fernet(cfg.get("KYC_ENCRYPTION_KEY") or cfg["SECRET_KEY"])


def encrypt_value(plain: str, fernet: Fernet = None) -> str:
    if not plain or plain == "NOT_PROVIDED":
        return plain
    return (fernet or _app_fernet()).encrypt(plain.encode()).decode()


def decrypt_value(token: str, fernet: Fernet = None) -> str:
    if not token or token == "NOT_PROVIDED":
        return token
    try:
        return (fernet or _app_fernet()).decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return "[unreadable]"


def mask(value: str, keep: int = 4) -> str:
    if not value or value in ("NOT_PROVIDED", "[unreadable]"):
        return value or ""
    return "•" * max(len(value) - keep, 4) + value[-keep:]


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email or ""))


def encrypt_legacy_rows(conn, secret: str) -> int:
    f = _fernet(secret)
    rows = conn.execute("SELECT id, government_id FROM kyc").fetchall()
    changed = 0
    for row in rows:
        gid = row["government_id"]
        if gid and gid != "NOT_PROVIDED" and not gid.startswith("gAAAA"):
            conn.execute("UPDATE kyc SET government_id = ? WHERE id = ?", (f.encrypt(gid.encode()).decode(), row["id"]))
            changed += 1
    return changed
