"""SQLite access for CrossPay.

One connection per request, stored on flask.g and closed in teardown_appcontext (M6).
init_db() creates tables, applies additive column migrations and seeds demo data once.
"""
import os
import secrets
import sqlite3
from datetime import datetime, timezone

from flask import current_app, g
from werkzeug.security import generate_password_hash


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect(current_app.config["DB_PATH"])
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'sme',
        created_at TEXT NOT NULL
    )""",
    """
    CREATE TABLE IF NOT EXISTS kyc (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        business_name TEXT NOT NULL,
        country TEXT NOT NULL,
        business_type TEXT NOT NULL,
        government_id TEXT NOT NULL,
        address TEXT NOT NULL,
        status TEXT DEFAULT 'PENDING',
        verification_notes TEXT,
        submitted_at TEXT,
        verified_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""",
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        sender TEXT NOT NULL,
        receiver TEXT NOT NULL,
        sender_country TEXT NOT NULL,
        receiver_country TEXT NOT NULL,
        currency TEXT NOT NULL,
        amount REAL NOT NULL,
        source_currency TEXT,
        target_currency TEXT,
        exchange_rate REAL DEFAULT 1.0,
        converted_amount REAL,
        exchange_rate_provider TEXT,
        rate_timestamp TEXT,
        normalized_usd_amount REAL,
        frequency INTEGER NOT NULL,
        previous_transactions INTEGER NOT NULL,
        suspicious_transactions INTEGER NOT NULL,
        account_age INTEGER NOT NULL,
        corridor_risk REAL DEFAULT 0.25,
        risk_level TEXT NOT NULL,
        risk_score REAL NOT NULL,
        decision TEXT NOT NULL,
        blockchain_hash TEXT,
        smart_contract_status TEXT NOT NULL,
        block_number INTEGER,
        notes TEXT,
        timestamp TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""",
]

# Additive migrations: (table, column, definition). Applied when the column is missing.
COLUMNS = []


def init_db(app) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(app.config["DB_PATH"])), exist_ok=True)
    conn = connect(app.config["DB_PATH"])
    try:
        for stmt in SCHEMA:
            conn.execute(stmt)
        for table, col, definition in COLUMNS:
            existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            if col not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            seed_initial_data(conn, app.config)
    finally:
        conn.close()


def seed_initial_data(conn: sqlite3.Connection, config) -> None:
    now = utcnow_iso()
    # C2: seed passwords come from the environment; when unset they are random and unknown to anyone
    # (the demo accounts are then reachable only through /quick_login, which exists only in DEMO_MODE).
    sme_pwd = generate_password_hash(config.get("DEMO_SME_PASSWORD") or secrets.token_urlsafe(18), method=config.get("PASSWORD_HASH_METHOD", "scrypt"))
    admin_pwd = generate_password_hash(config.get("DEMO_ADMIN_PASSWORD") or secrets.token_urlsafe(18), method=config.get("PASSWORD_HASH_METHOD", "scrypt"))
    conn.execute("BEGIN")
    cur = conn.execute(
        "INSERT INTO users (name, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)",
        ("Global Logistics Ltd (SME Demo)", "demo@globallogistics.com", sme_pwd, "sme", now),
    )
    sme_id = cur.lastrowid
    conn.execute(
        "INSERT INTO users (name, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)",
        ("Compliance Administrator", "admin@crosspay.org", admin_pwd, "admin", now),
    )
    conn.execute(
        """INSERT INTO kyc (user_id, business_name, country, business_type, government_id, address,
               status, verification_notes, submitted_at, verified_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (sme_id, "Global Logistics SME Ltd", "United States", "Import/Export Trade SME", "US-EIN-984721094",
         "124 Financial District Blvd, New York, NY 10004", "VERIFIED",
         "Automated Tax ID and SME Registry Validation Successful", now, now),
    )
    seed = [
        ("TX-2026-8801", "EuroTech Industrial Gmbh", "Germany", 5400.00, "EUR", 0.92, 4968.00, 2, 48, 0, 28, 0.20,
         "LOW", 8.4, "APPROVED", "0x7c4f68b3d0a98f121e78c85e2bfa7c9082ef45b91b8a924467d5e4b2d189f3a1",
         "EXECUTED_SETTLED", 1, "Raw material component purchase - Invoice #8801"),
        ("TX-2026-8802", "Apex Pacific Trade Corp", "Brazil", 28500.00, "EUR", 0.92, 26220.00, 7, 6, 1, 6, 0.55,
         "MEDIUM", 62.8, "HOLD", "PENDING_ADDITIONAL_VERIFICATION", "HELD_IN_ESCROW", None,
         "High volume overseas electronics shipment batch"),
        ("TX-2026-8803", "Shadow Frontier Express", "Nigeria", 145000.00, "INR", 83.25, 12071250.00, 19, 1, 4, 1, 0.88,
         "HIGH", 94.6, "BLOCKED", "NOT RECORDED (POLICY REJECT)", "REJECTED_BLOCKED", None,
         "Unverified overseas offshore consulting fee"),
    ]
    for (tx_id, receiver, rc, amount, tgt, rate, conv, freq, prev, susp, age, corr, level, score, decision,
         bhash, sc_status, block, notes) in seed:
        conn.execute(
            """INSERT INTO transactions (
                transaction_id, user_id, sender, receiver, sender_country, receiver_country,
                currency, amount, source_currency, target_currency, exchange_rate, converted_amount,
                exchange_rate_provider, rate_timestamp, normalized_usd_amount,
                frequency, previous_transactions, suspicious_transactions, account_age, corridor_risk,
                risk_level, risk_score, decision, blockchain_hash, smart_contract_status, block_number, notes, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tx_id, sme_id, "Global Logistics SME Ltd", receiver, "United States", rc, "USD", amount, "USD", tgt,
             rate, conv, "ExchangeRate-API", now, amount, freq, prev, susp, age, corr, level, score, decision, bhash,
             sc_status, block, notes, now),
        )
    conn.execute("COMMIT")
