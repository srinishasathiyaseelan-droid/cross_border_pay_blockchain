"""Model features, derived on the server (C4, L1).

All seven Random Forest features come from the database and the converted amount. Nothing the sender
types (apart from the amount and the corridor) reaches the model.
"""
from datetime import datetime, timedelta, timezone

FEATURE_NAMES = [
    "amount",                   # USD-normalised amount of this payment
    "frequency",                # this SME's payments in the last 30 days
    "previous_transactions",    # this SME's total payments before this one
    "suspicious_transactions",  # this SME's payments that ended HOLD, BLOCKED or REJECTED
    "account_age",              # whole months since users.created_at (minimum 1)
    "corridor_risk",            # weighted country risk of sender and receiver
    "amount_to_age_ratio",      # amount / (account_age + 0.5)
]

COUNTRY_RISK_MAP = {
    "United States": 0.18, "United Kingdom": 0.20, "Germany": 0.15, "Singapore": 0.16, "Japan": 0.17,
    "Canada": 0.19, "Australia": 0.18, "France": 0.21, "India": 0.40, "Brazil": 0.52,
    "United Arab Emirates": 0.38, "Mexico": 0.48, "South Africa": 0.58, "Nigeria": 0.85, "Russia": 0.82,
    "Pakistan": 0.78,
}
ALLOWED_COUNTRIES = sorted(COUNTRY_RISK_MAP)

# DEMO_MODE only: fixed behavioural vectors for the three viva scenarios. The receipt is badged "DEMO VECTOR".
DEMO_VECTORS = {
    "low": {"frequency": 2, "previous_transactions": 48, "suspicious_transactions": 0, "account_age": 26},
    "medium": {"frequency": 5, "previous_transactions": 12, "suspicious_transactions": 0, "account_age": 10},
    "high": {"frequency": 19, "previous_transactions": 1, "suspicious_transactions": 4, "account_age": 1},
}


class FeatureError(ValueError):
    pass


def corridor_risk(sender_country: str, receiver_country: str) -> float:
    if sender_country not in COUNTRY_RISK_MAP or receiver_country not in COUNTRY_RISK_MAP:
        raise FeatureError("Unsupported country: choose sender and receiver countries from the list.")
    r1, r2 = COUNTRY_RISK_MAP[sender_country], COUNTRY_RISK_MAP[receiver_country]
    return round((r1 + r2 * 1.5) / 2.5, 3)


def _parse_ts(value: str) -> datetime:
    value = (value or "").strip().replace("Z", "+00:00")
    for fmt in (None, "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.fromisoformat(value) if fmt is None else datetime.strptime(value, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.now(timezone.utc)


def months_between(start: datetime, end: datetime) -> int:
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(1, months)


def build_features(conn, user_id: int, amount_usd: float, sender_country: str, receiver_country: str,
                   now: datetime = None) -> dict:
    now = now or datetime.now(timezone.utc)
    user = conn.execute("SELECT created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        raise FeatureError("Unknown user")
    since = (now - timedelta(days=30)).isoformat().replace("+00:00", "Z")
    # Count only settled history rows (not a PENDING row of the payment being decided).
    base = "FROM transactions WHERE user_id = ? AND decision NOT IN ('PENDING_SETTLEMENT')"
    frequency = conn.execute(f"SELECT COUNT(*) {base} AND timestamp >= ?", (user_id, since)).fetchone()[0]
    previous = conn.execute(f"SELECT COUNT(*) {base}", (user_id,)).fetchone()[0]
    suspicious = conn.execute(
        f"SELECT COUNT(*) {base} AND (decision IN ('HOLD', 'BLOCKED', 'REJECTED') "
        "OR transaction_id IN (SELECT tx_id FROM hold_reviews))", (user_id,)
    ).fetchone()[0] if _has_table(conn, "hold_reviews") else conn.execute(
        f"SELECT COUNT(*) {base} AND decision IN ('HOLD', 'BLOCKED', 'REJECTED')", (user_id,)
    ).fetchone()[0]
    account_age = months_between(_parse_ts(user["created_at"]), now)
    amount = round(float(amount_usd), 2)
    return {
        "amount": amount,
        "frequency": int(frequency),
        "previous_transactions": int(previous),
        "suspicious_transactions": int(suspicious),
        "account_age": int(account_age),
        "corridor_risk": corridor_risk(sender_country, receiver_country),
        "amount_to_age_ratio": round(amount / (account_age + 0.5), 2),
    }


def apply_demo_vector(features: dict, scenario: str) -> dict:
    vec = DEMO_VECTORS[scenario]
    out = {**features, **vec}
    out["amount_to_age_ratio"] = round(out["amount"] / (out["account_age"] + 0.5), 2)
    return out


def _has_table(conn, name: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None
