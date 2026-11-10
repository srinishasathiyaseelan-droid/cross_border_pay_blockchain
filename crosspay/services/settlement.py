"""Atomic settlement (H2, M3, M9).

Order inside ONE SQLite transaction (BEGIN IMMEDIATE):
  claim idempotency key -> INSERT row as PENDING_SETTLEMENT -> policy decision -> build PoW block in memory
  -> UPDATE row -> append HMAC audit record (carrying the block) -> COMMIT
Only after COMMIT is the derived explorer JSON rewritten. Any exception rolls everything back: no row, no audit
record, no block.
"""
import json
import logging

from flask import current_app

from ..db import utcnow_iso
from ..realtime import publish_safely, settlement_event
from ..ledger.chain import NOT_RECORDED, settlement_record, tx_hash
from ..security import idempotency
from ..util import new_tx_id

log = logging.getLogger(__name__)


class DuplicateSubmission(Exception):
    def __init__(self, tx_id):
        super().__init__(tx_id)
        self.tx_id = tx_id


class SettlementError(Exception):
    pass


def _ext(name):
    return current_app.extensions[name]


def _finish(conn):
    try:
        _ext("ledger").export_view(conn)
    except Exception:  # noqa: BLE001 — the view is derived and rebuilt on the next commit
        log.exception("Ledger view export failed after commit")


def settle_payment(conn, *, user_id, kyc_status, data, conversion, features, scored, feature_source,
                   idempotency_key=None, overrides=(), ai_escalations=(), extra_columns=None) -> dict:
    ledger, audit, contract = _ext("ledger"), _ext("audit"), _ext("contract")
    conn.execute("BEGIN IMMEDIATE")
    try:
        if idempotency_key:
            existing = idempotency.claim(conn, user_id, idempotency_key)
            if existing:
                conn.execute("ROLLBACK")
                raise DuplicateSubmission(existing)
        tx_id = new_tx_id()
        now = utcnow_iso()
        row = {
            "transaction_id": tx_id, "user_id": user_id, "sender": data["sender"], "receiver": data["receiver"],
            "sender_country": data["sender_country"], "receiver_country": data["receiver_country"],
            "currency": conversion["source_currency"], "amount": conversion["original_amount"],
            "source_currency": conversion["source_currency"], "target_currency": conversion["target_currency"],
            "exchange_rate": conversion["exchange_rate"], "converted_amount": conversion["converted_amount"],
            "exchange_rate_provider": conversion["provider"], "rate_timestamp": conversion["last_updated"],
            "rate_stale": 1 if conversion.get("stale") else 0,
            "normalized_usd_amount": conversion["normalized_usd_amount"],
            "frequency": features["frequency"], "previous_transactions": features["previous_transactions"],
            "suspicious_transactions": features["suspicious_transactions"], "account_age": features["account_age"],
            "corridor_risk": features["corridor_risk"], "amount_to_age_ratio": features["amount_to_age_ratio"],
            "risk_level": scored["level"], "risk_score": scored["score"], "p_low": scored["p_low"],
            "p_med": scored["p_med"], "p_high": scored["p_high"], "scoring_engine": scored["engine"],
            "top_factors": json.dumps(scored["top_factors"]), "feature_source": feature_source,
            "decision": "PENDING_SETTLEMENT", "smart_contract_status": "PENDING", "notes": data.get("notes", ""),
            "timestamp": now, "idempotency_key": idempotency_key, **(extra_columns or {}),
        }
        cols = ",".join(row)
        conn.execute(f"INSERT INTO transactions ({cols}) VALUES ({','.join('?' * len(row))})", list(row.values()))

        decision = contract.decide(kyc_status, scored["level"], scored["score"], overrides=overrides,
                                   ai_escalations=ai_escalations)
        record = settlement_record(row, decision.decision, now)
        block = None
        if decision.decision == "APPROVED":
            h = tx_hash(record)
            block = ledger.build_block(conn, {**record, "tx_hash": h}, now)
            label = h
        else:
            label = NOT_RECORDED[decision.decision] if decision.decision != "REJECTED" else "NOT RECORDED (KYC UNVERIFIED)"
        conn.execute(
            """UPDATE transactions SET decision = ?, smart_contract_status = ?, blockchain_hash = ?, block_number = ?,
                   policy_reasons = ?, decided_at = ? WHERE transaction_id = ?""",
            (decision.decision, decision.contract_status, label, block.index if block else None,
             json.dumps(decision.reason_codes), now, tx_id),
        )
        audit.append(conn, "decision", tx_id, {
            "record": record, "decision": decision.decision, "tx_hash_or_label": label,
            "reasons": decision.reason_codes, "policy_id": decision.policy_id, "features": features,
            "scoring": {k: scored[k] for k in ("level", "score", "p_low", "p_med", "p_high", "engine")},
            "feature_source": feature_source, "block": block.to_dict() if block else None,
        })
        if idempotency_key:
            idempotency.bind(conn, user_id, idempotency_key, tx_id)
        conn.execute("COMMIT")
    except DuplicateSubmission:
        raise
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    _finish(conn)
    publish_safely(current_app._get_current_object(),
                   settlement_event("decision", row, decision.decision, block.index if block else None))
    return {"tx_id": tx_id, "decision": decision.decision, "block": block.index if block else None}


def resolve_hold(conn, *, tx_id, admin_id, action, reason, copilot_memo=None, ai_draft=None, ai_agreement=None) -> dict:
    """Officer releases (mines) or rejects a HOLD. KYC is re-checked before release (M9)."""
    ledger, audit = _ext("ledger"), _ext("audit")
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT * FROM transactions WHERE transaction_id = ?", (tx_id,)).fetchone()
        if row is None or row["decision"] != "HOLD":
            raise SettlementError("Transaction is not in HOLD state.")
        row = dict(row)
        kyc = conn.execute("SELECT status FROM kyc WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                           (row["user_id"],)).fetchone()
        kyc_status = kyc["status"] if kyc else "MISSING"
        now = utcnow_iso()
        block = None
        if action == "approve":
            if kyc_status != "VERIFIED":
                raise SettlementError(f"Cannot release: the SME's KYC is now {kyc_status}. Reject or wait for re-verification.")
            record = settlement_record(row, "APPROVED", now)
            h = tx_hash(record)
            block = ledger.build_block(conn, {**record, "tx_hash": h}, now)
            new_decision, status, label = "APPROVED", "EXECUTED_SETTLED_POST_AUDIT", h
        elif action == "reject":
            record = settlement_record(row, "REJECTED", now)
            new_decision, status, label = "REJECTED", "REJECTED_BY_COMPLIANCE", "NOT RECORDED (REJECTED BY COMPLIANCE)"
        else:
            raise SettlementError("Unknown action.")
        conn.execute(
            """UPDATE transactions SET decision = ?, smart_contract_status = ?, blockchain_hash = ?, block_number = ?,
                   decided_at = ? WHERE transaction_id = ?""",
            (new_decision, status, label, block.index if block else None, now, tx_id),
        )
        conn.execute(
            """INSERT INTO hold_reviews (tx_id, admin_id, action, reason, copilot_memo, ai_draft, ai_agreement,
                   kyc_status_at_review, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tx_id, admin_id, action, reason, copilot_memo, ai_draft, ai_agreement, kyc_status, now),
        )
        audit.append(conn, "release" if block else "reject", tx_id, {
            "record": record, "decision": new_decision, "tx_hash_or_label": label, "reviewer_id": admin_id,
            "reason": reason, "block": block.to_dict() if block else None,
        })
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    _finish(conn)
    publish_safely(current_app._get_current_object(),
                   settlement_event("review", row, new_decision, block.index if block else None))
    return {"tx_id": tx_id, "decision": new_decision, "block": block.index if block else None}


def bootstrap_ledger(conn, ledger, audit) -> int:
    """M3: give fixture/legacy rows that have no audit record a signed record (and a block if APPROVED), in id
    order, so the DB and the ledger describe the same history. Runs once at startup; idempotent."""
    rows = conn.execute(
        "SELECT * FROM transactions WHERE transaction_id NOT IN (SELECT tx_id FROM audit_chain) "
        "AND decision != 'PENDING_SETTLEMENT' ORDER BY id ASC").fetchall()
    if not rows:
        return 0
    conn.execute("BEGIN IMMEDIATE")
    try:
        for r in rows:
            row = dict(r)
            decided_at = row.get("decided_at") or row.get("timestamp") or utcnow_iso()
            record = settlement_record(row, row["decision"], decided_at)
            block = None
            label = row.get("blockchain_hash")
            if row["decision"] == "APPROVED":
                h = tx_hash(record)
                block = ledger.build_block(conn, {**record, "tx_hash": h}, decided_at)
                label = h
            conn.execute("UPDATE transactions SET blockchain_hash = ?, block_number = ?, decided_at = ? "
                         "WHERE transaction_id = ?", (label, block.index if block else None, decided_at,
                                                      row["transaction_id"]))
            audit.append(conn, "seed", row["transaction_id"], {
                "record": record, "decision": row["decision"], "tx_hash_or_label": label,
                "block": block.to_dict() if block else None, "note": "fixture or pre-hardening row",
            })
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return len(rows)
