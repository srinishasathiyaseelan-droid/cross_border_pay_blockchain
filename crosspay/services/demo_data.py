"""DEMO_MODE only: a one-time top-up of labelled demo data so the dashboards, the live console and the review queue
have something to show.

Every payment is decided the same way a live one is: features come from the real feature builder over the SME's
history *at that time* (payments are added oldest first), the real Random Forest scores them, and the real policy
engine decides. The rows are then signed into the HMAC audit chain and APPROVED ones mined into the PoW ledger by
``bootstrap_ledger`` (the same path fixtures use), so ``Ledger.verify`` stays valid.

What it does NOT do: no FX calls (fixed demo rates, labelled), no AI calls, no officer reviews or copilot rows, no
real people or companies (every name starts with "Demo"). It runs once, recorded by a marker row in ai_settings.
"""
import json
import logging
import random
import secrets
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from ..db import _iso
from ..policy.engine import STATUS
from .features import ALLOWED_COUNTRIES, COUNTRY_RISK_MAP, build_features, velocity_1h

log = logging.getLogger(__name__)

MARKER = "demo_dataset_v1"
PAYMENTS = 80
MIN_HOLDS = 6
DAYS = 120  # about two payments per SME per 30 days: realistic frequency for the model's features

# Fixed, labelled demo rates (target units per 1 USD). Never shown as live rates.
DEMO_RATES = {"USD": 1.0, "EUR": 0.92, "GBP": 0.79, "SGD": 1.35, "JPY": 151.0, "INR": 83.2, "AED": 3.67,
              "AUD": 1.52, "CAD": 1.37}
DEMO_SMES = [
    # name, country, business type, months since the account opened
    ("Demo Andes Textiles SA", "United States", "Textile importer", 30),
    ("Demo Rhine Precision Parts GmbH", "Germany", "Machine parts manufacturer", 18),
    ("Demo Lion City Electronics Pte", "Singapore", "Electronics distributor", 9),
    ("Demo Thames Organic Foods Ltd", "United Kingdom", "Food wholesaler", 4),
    ("Demo Deccan Pharma Supplies", "India", "Pharmaceutical supplies", 14),
    ("Demo Maple Timber Co", "Canada", "Timber exporter", 40),
    ("Demo Outback Wool Traders", "Australia", "Wool trader", 26),
    ("Demo Seine Fashion House", "France", "Apparel importer", 22),
    ("Demo Gulf Spice Traders LLC", "United Arab Emirates", "Spice importer", 12),
    ("Demo Sakura Robotics KK", "Japan", "Robotics distributor", 36),
]
RECEIVERS = ["Demo Supplier Alpha", "Demo Components Beta", "Demo Freight Gamma", "Demo Trading Delta",
             "Demo Materials Epsilon", "Demo Logistics Zeta", "Demo Packaging Eta", "Demo Consulting Theta"]
PURPOSES = ["Demo invoice: raw materials", "Demo invoice: machine parts", "Demo invoice: freight charges",
            "Demo invoice: packaging", "Demo invoice: consulting retainer", "Demo invoice: electronics batch"]
# Amount bands (USD) and how often each is drawn: mostly ordinary trade, a tail of large payments.
AMOUNT_BANDS = [((800, 9_000), 0.80), ((9_000, 60_000), 0.15), ((60_000, 180_000), 0.05)]
HISTORY_PER_SME = 6  # older small payments: an established track record, as real SMEs have


def applied(conn) -> bool:
    return conn.execute("SELECT 1 FROM ai_settings WHERE key = ?", (MARKER,)).fetchone() is not None


def _currency(country: str) -> str:
    from .currency import COUNTRY_TO_DEFAULT_CURRENCY

    cur = COUNTRY_TO_DEFAULT_CURRENCY.get(country, "USD")
    return cur if cur in DEMO_RATES else "USD"


def _amount(rng) -> float:
    r, acc = rng.random(), 0.0
    for (lo, hi), p in AMOUNT_BANDS:
        acc += p
        if r <= acc:
            return round(rng.uniform(lo, hi), 2)
    return round(rng.uniform(800, 12_000), 2)


def _ensure_smes(conn, now: datetime, hash_method: str) -> list:
    ids = []
    for name, country, btype, months in DEMO_SMES:
        email = name.lower().replace(" ", ".").replace(".pte", "").replace(".gmbh", "") + "@demo.invalid"
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            ids.append((row[0], country))
            continue
        opened = _iso(now - timedelta(days=31 * months))
        # A random password nobody knows: these accounts exist only to give the officer views some volume.
        pwd = generate_password_hash(secrets.token_urlsafe(18), method=hash_method)
        uid = conn.execute("INSERT INTO users (name, email, password, role, created_at) VALUES (?, ?, ?, 'sme', ?)",
                           (name, email, pwd, opened)).lastrowid
        conn.execute(
            """INSERT INTO kyc (user_id, business_name, country, business_type, government_id, address, status,
                   verification_notes, submitted_at, verified_at) VALUES (?, ?, ?, ?, ?, ?, 'VERIFIED', ?, ?, ?)""",
            (uid, name, country, btype, f"DEMO-ID-{uid:04d}", "Demo address (not real)", "Demo data: verified by the demo seed",
             opened, opened))
        ids.append((uid, country))
    return ids


def seed(app, conn, rng: random.Random = None, payments: int = PAYMENTS, now: datetime = None) -> dict:
    """Idempotent. -> {"applied": bool, "smes": n, "payments": n, "by_decision": {...}}"""
    if applied(conn):
        return {"applied": False, "reason": "already applied"}
    from .settlement import bootstrap_ledger
    from ..util import new_tx_id

    rng = rng or random.Random(20261110)
    now = now or datetime.now(timezone.utc)
    scorer, contract = app.extensions["scorer"], app.extensions["contract"]
    conn.execute("BEGIN IMMEDIATE")
    if applied(conn):  # re-check under the write lock: the startup thread and the CLI may race
        conn.execute("ROLLBACK")
        return {"applied": False, "reason": "already applied"}
    try:
        smes = _ensure_smes(conn, now, app.config.get("PASSWORD_HASH_METHOD", "scrypt"))
        # Oldest first, at least two days old, so each payment's features see only earlier history and nothing
        # here is inside the last hour (VELOCITY_BURST) or today's AI budget window.
        # Phase 1 (5-12 months ago): each SME's small, ordinary history. Phase 2 (last DAYS days): the mix.
        plan = [(now - timedelta(days=rng.uniform(150, 365)), uid, country, True)
                for uid, country in smes for _ in range(HISTORY_PER_SME)]
        plan += [(now - timedelta(days=rng.uniform(2, DAYS), minutes=rng.randint(0, 600)),) + rng.choice(smes) + (False,)
                 for _ in range(payments)]
        plan.sort(key=lambda p: p[0])
        times = [p[0] for p in plan]
        counts, extra = {}, 0
        i = 0
        while i < len(times):
            ts = times[i]
            if i < len(plan):
                _, uid, sender_country, history = plan[i]
            else:  # top-up for the review queue
                (uid, sender_country), history = rng.choice(smes), False
            # Mostly ordinary trade corridors; about one payment in eight goes to a high-risk corridor.
            pool = [c for c in ALLOWED_COUNTRIES if c != sender_country]
            risky = [c for c in pool if COUNTRY_RISK_MAP[c] >= 0.45]
            receiver_country = rng.choice(risky if (not history and rng.random() < 0.10) else [c for c in pool if c not in risky])
            amount = (round(rng.uniform(800, 6_000), 2) if history else
                      round(rng.uniform(12_000, 60_000), 2) if i >= len(plan) else _amount(rng))
            features = build_features(conn, uid, amount, sender_country, receiver_country, now=ts)
            scored = scorer.score(features)
            burst_at = int(app.config.get("VELOCITY_BURST_1H") or 0)
            overrides = ["VELOCITY_BURST"] if burst_at and velocity_1h(conn, uid, ts) + 1 >= burst_at else []
            decision = contract.decide("VERIFIED", scored["level"], scored["score"], overrides=overrides)
            target = _currency(receiver_country)
            row = {
                "transaction_id": new_tx_id(), "user_id": uid, "sender": dict(DEMO_SMES_BY_COUNTRY).get(sender_country),
                "receiver": rng.choice(RECEIVERS), "sender_country": sender_country,
                "receiver_country": receiver_country, "currency": "USD", "amount": amount, "source_currency": "USD",
                "target_currency": target, "exchange_rate": DEMO_RATES[target],
                "converted_amount": round(amount * DEMO_RATES[target], 2),
                "exchange_rate_provider": "demo seed (fixed rate)", "rate_timestamp": _iso(ts), "rate_stale": 0,
                "normalized_usd_amount": amount, **{k: features[k] for k in (
                    "frequency", "previous_transactions", "suspicious_transactions", "account_age", "corridor_risk",
                    "amount_to_age_ratio")},
                "risk_level": scored["level"], "risk_score": scored["score"], "p_low": scored["p_low"],
                "p_med": scored["p_med"], "p_high": scored["p_high"], "scoring_engine": scored["engine"],
                "top_factors": json.dumps(scored["top_factors"]), "feature_source": "demo_seed",
                "decision": decision.decision, "smart_contract_status": STATUS[decision.decision],
                "blockchain_hash": None if decision.decision == "APPROVED" else "NOT RECORDED (DEMO SEED)",
                "policy_reasons": json.dumps(decision.reason_codes), "notes": rng.choice(PURPOSES),
                "timestamp": _iso(ts), "decided_at": _iso(ts),
            }
            if history and decision.decision != "APPROVED":
                continue  # the track record is, by definition, payments that settled; redraw this one
            cols = ",".join(row)
            conn.execute(f"INSERT INTO transactions ({cols}) VALUES ({','.join('?' * len(row))})", list(row.values()))
            counts[decision.decision] = counts.get(decision.decision, 0) + 1
            i += 1
            # Make sure the review queue has items: a few more ordinary-sized payments if the draw gave too few HOLDs.
            if i == len(times) and counts.get("HOLD", 0) < MIN_HOLDS and extra < 30:
                times.append(min(times[-1] + timedelta(minutes=rng.randint(70, 400)), now - timedelta(days=1)))
                extra += 1
        conn.execute("INSERT INTO ai_settings (key, value) VALUES (?, ?)", (MARKER, _iso(now)))
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    signed = bootstrap_ledger(conn, app.extensions["ledger"], app.extensions["audit"])
    app.extensions["ledger"].export_view(conn)
    out = {"applied": True, "smes": len(smes), "payments": sum(counts.values()), "by_decision": counts,
           "signed": signed}
    log.info("Demo dataset added: %s", out)
    return out


DEMO_SMES_BY_COUNTRY = [(c, n) for n, c, _, _ in DEMO_SMES]
