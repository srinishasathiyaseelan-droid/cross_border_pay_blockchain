"""
Database management module for SQLite.
Handles connection, schema initialization, and helper functions.
"""

import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'sme',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # KYC Table
    cursor.execute("""
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
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        verified_at TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # Transactions Table
    cursor.execute("""
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
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # Non-destructive migration for existing databases: check and add missing columns
    cursor.execute("PRAGMA table_info(transactions)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    columns_to_add = [
        ("source_currency", "TEXT"),
        ("target_currency", "TEXT"),
        ("exchange_rate", "REAL DEFAULT 1.0"),
        ("converted_amount", "REAL"),
        ("exchange_rate_provider", "TEXT"),
        ("rate_timestamp", "TEXT"),
        ("normalized_usd_amount", "REAL")
    ]

    for col_name, col_def in columns_to_add:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE transactions ADD COLUMN {col_name} {col_def}")

    # Backfill legacy records if any are missing source_currency
    cursor.execute("""
        UPDATE transactions
        SET source_currency = COALESCE(source_currency, currency, 'USD'),
            target_currency = COALESCE(target_currency, currency, 'USD'),
            exchange_rate = COALESCE(exchange_rate, 1.0),
            converted_amount = COALESCE(converted_amount, amount),
            exchange_rate_provider = COALESCE(exchange_rate_provider, 'Legacy Initial Snapshot'),
            rate_timestamp = COALESCE(rate_timestamp, timestamp),
            normalized_usd_amount = COALESCE(normalized_usd_amount, amount)
        WHERE source_currency IS NULL OR target_currency IS NULL
    """)

    conn.commit()

    # Seed initial demo data if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        seed_initial_data(conn)

    conn.close()

def seed_initial_data(conn):
    cursor = conn.cursor()
    
    # Create Default SME User and Admin User
    sme_pwd = generate_password_hash("sme123")
    admin_pwd = generate_password_hash("admin123")
    
    cursor.execute("""
    INSERT INTO users (name, email, password, role)
    VALUES (?, ?, ?, ?)
    """, ("Global Logistics Ltd (SME Demo)", "demo@globallogistics.com", sme_pwd, "sme"))
    sme_id = cursor.lastrowid

    cursor.execute("""
    INSERT INTO users (name, email, password, role)
    VALUES (?, ?, ?, ?)
    """, ("Compliance Administrator", "admin@crosspay.org", admin_pwd, "admin"))

    # Seed Verified KYC for the SME Demo user
    cursor.execute("""
    INSERT INTO kyc (user_id, business_name, country, business_type, government_id, address, status, verification_notes, verified_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sme_id,
        "Global Logistics SME Ltd",
        "United States",
        "Import/Export Trade SME",
        "US-EIN-984721094",
        "124 Financial District Blvd, New York, NY 10004",
        "VERIFIED",
        "Automated Tax ID and SME Registry Validation Successful",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    # Seed Sample Transactions showing PPT Scenarios
    # Scenario 1 - Low Risk -> Approved -> Recorded on Blockchain (USD -> EUR conversion demo)
    cursor.execute("""
    INSERT INTO transactions (
        transaction_id, user_id, sender, receiver, sender_country, receiver_country,
        currency, amount, source_currency, target_currency, exchange_rate, converted_amount,
        exchange_rate_provider, rate_timestamp, normalized_usd_amount,
        frequency, previous_transactions, suspicious_transactions,
        account_age, corridor_risk, risk_level, risk_score, decision, blockchain_hash,
        smart_contract_status, block_number, notes, timestamp
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "TX-2026-8801", sme_id, "Global Logistics SME Ltd", "EuroTech Industrial Gmbh",
        "United States", "Germany", "USD", 5400.00,
        "USD", "EUR", 0.9200, 4968.00, "ExchangeRate-API", datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"), 5400.00,
        2, 48, 0, 28, 0.20,
        "LOW", 8.4, "APPROVED",
        "0x7c4f68b3d0a98f121e78c85e2bfa7c9082ef45b91b8a924467d5e4b2d189f3a1",
        "EXECUTED_SETTLED", 1, "Raw material component purchase - Invoice #8801",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    # Scenario 2 - Medium Risk -> Hold -> Pending Review (USD -> EUR conversion demo)
    cursor.execute("""
    INSERT INTO transactions (
        transaction_id, user_id, sender, receiver, sender_country, receiver_country,
        currency, amount, source_currency, target_currency, exchange_rate, converted_amount,
        exchange_rate_provider, rate_timestamp, normalized_usd_amount,
        frequency, previous_transactions, suspicious_transactions,
        account_age, corridor_risk, risk_level, risk_score, decision, blockchain_hash,
        smart_contract_status, block_number, notes, timestamp
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "TX-2026-8802", sme_id, "Global Logistics SME Ltd", "Apex Pacific Trade Corp",
        "United States", "Brazil", "USD", 28500.00,
        "USD", "EUR", 0.9200, 26220.00, "ExchangeRate-API", datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"), 28500.00,
        7, 6, 1, 6, 0.55,
        "MEDIUM", 62.8, "HOLD",
        "PENDING_ADDITIONAL_VERIFICATION",
        "HELD_IN_ESCROW", None, "High volume overseas electronics shipment batch",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    # Scenario 3 - High Risk -> Blocked -> Not Recorded on Blockchain (USD -> INR conversion demo)
    cursor.execute("""
    INSERT INTO transactions (
        transaction_id, user_id, sender, receiver, sender_country, receiver_country,
        currency, amount, source_currency, target_currency, exchange_rate, converted_amount,
        exchange_rate_provider, rate_timestamp, normalized_usd_amount,
        frequency, previous_transactions, suspicious_transactions,
        account_age, corridor_risk, risk_level, risk_score, decision, blockchain_hash,
        smart_contract_status, block_number, notes, timestamp
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "TX-2026-8803", sme_id, "Global Logistics SME Ltd", "Shadow Frontier Express",
        "United States", "Nigeria", "USD", 145000.00,
        "USD", "INR", 83.2500, 12071250.00, "ExchangeRate-API", datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"), 145000.00,
        19, 1, 4, 1, 0.88,
        "HIGH", 94.6, "BLOCKED",
        "NOT RECORDED (POLICY REJECT)",
        "REJECTED_BLOCKED", None, "Unverified overseas offshore consulting fee",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()

if __name__ == "__main__":
    init_db()
    print(f"Database initialized successfully at: {DB_PATH}")

