"""Compliance administration. Every route here requires an admin account (C1)."""
from flask import Blueprint, current_app, flash, redirect, request, url_for

from ..db import get_db
from ..security.decorators import admin_required

bp = Blueprint("admin", __name__)


@bp.route("/resolve_hold/<tx_id>", methods=["POST"])
@admin_required
def resolve_hold(tx_id):
    action = request.form.get("action", "approve")
    conn = get_db()
    tx = conn.execute("SELECT * FROM transactions WHERE transaction_id = ?", (tx_id,)).fetchone()
    if not tx or tx["decision"] != "HOLD":
        flash("Invalid transaction or transaction is not in HOLD state.", "warning")
        return redirect(url_for("payments.transactions"))

    if action == "approve":
        rel = current_app.extensions["contract"].release_hold(dict(tx))
        conn.execute(
            """UPDATE transactions SET decision = 'APPROVED', smart_contract_status = 'EXECUTED_SETTLED_POST_AUDIT',
                   blockchain_hash = ?, block_number = ? WHERE transaction_id = ?""",
            (rel["tx_hash"], rel["block_number"], tx_id),
        )
        flash(f"Transaction {tx_id} approved after secondary compliance review. "
              f"Mined to Block #{rel['block_number']}.", "success")
    else:
        conn.execute(
            """UPDATE transactions SET decision = 'BLOCKED', smart_contract_status = 'REJECTED_AUDIT_FAILED',
                   blockchain_hash = 'REJECTED_BY_COMPLIANCE' WHERE transaction_id = ?""",
            (tx_id,),
        )
        flash(f"Transaction {tx_id} rejected and permanently blocked by compliance officer.", "danger")
    return redirect(url_for("payments.transactions"))
