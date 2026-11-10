"""JSON API used by the UI."""
from urllib.parse import urlparse

from flask import Blueprint, abort, current_app, jsonify, request

from ..security.decorators import login_required

from ..services.currency import (
    COUNTRY_TO_DEFAULT_CURRENCY,
    SUPPORTED_CURRENCIES,
    ExchangeRateAPIError,
    InvalidAmountError,
    UnsupportedCurrencyError,
)

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.before_request
def _same_origin():
    """H4 for the JSON API (exempt from token CSRF): unsafe methods must come from this origin as JSON."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return None
    origin = request.headers.get("Origin") or request.headers.get("Referer")
    if not origin or urlparse(origin).netloc != request.host:
        abort(403)
    if not (request.is_json or request.mimetype == "multipart/form-data"):
        abort(415)
    return None


@bp.route("/validate_chain")
@login_required
def validate_chain():
    from ..db import get_db

    return jsonify(current_app.extensions["ledger"].verify(get_db()))


@bp.route("/metrics")
def metrics():
    return jsonify(current_app.extensions["metrics"])


@bp.route("/supported_currencies")
def supported_currencies():
    return jsonify({"success": True, "currencies": SUPPORTED_CURRENCIES,
                    "country_defaults": COUNTRY_TO_DEFAULT_CURRENCY})


@bp.route("/convert_currency", methods=["GET", "POST"])
def convert_currency():
    payload = (request.get_json(silent=True) or request.form) if request.method == "POST" else request.args
    amount = payload.get("amount")
    src = payload.get("source_currency") or payload.get("from")
    tgt = payload.get("target_currency") or payload.get("to")
    if not amount:
        return jsonify({"success": False, "error": "Parameter 'amount' is required."}), 400
    if not src or not tgt:
        return jsonify({"success": False, "error": "Both 'source_currency' and 'target_currency' are required."}), 400
    try:
        conversion = current_app.extensions["currency"].convert(amount=amount, source_currency=src,
                                                                 target_currency=tgt)
        return jsonify({"success": True, **conversion})
    except (InvalidAmountError, UnsupportedCurrencyError) as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except ExchangeRateAPIError as e:
        return jsonify({"success": False, "error": str(e)}), 503


@bp.route("/risk_preview", methods=["POST"])
@login_required
def risk_preview():
    """M5: the live preview runs the same feature builder and model as the real payment. Nothing is written."""
    from flask import session

    from ..db import get_db
    from ..services.features import FeatureError
    from .payments import PaymentInputError, assess, read_payment_form

    conn = get_db()
    kyc = conn.execute("SELECT * FROM kyc WHERE user_id = ? ORDER BY id DESC LIMIT 1", (session["user_id"],)).fetchone()
    if kyc is None:
        return jsonify({"success": False, "error": "KYC record missing"}), 400
    payload = request.get_json(silent=True) or {}
    payload.setdefault("receiver", "preview")
    try:
        data = read_payment_form(payload, kyc)
        conversion = current_app.extensions["currency"].convert(
            amount=data["amount"], source_currency=data["sender_currency"], target_currency=data["receiver_currency"])
        features, scored, source = assess(conn, session["user_id"], data, conversion)
    except (PaymentInputError, FeatureError, InvalidAmountError, UnsupportedCurrencyError) as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except ExchangeRateAPIError as e:
        return jsonify({"success": False, "error": str(e)}), 503
    decision = current_app.extensions["contract"].preview_decision(scored)
    return jsonify({"success": True, "level": scored["level"], "score": scored["score"], "engine": scored["engine"],
                    "decision": decision, "feature_source": source, "features": features,
                    "top_factors": scored["top_factors"]})


# ----------------- Advisory AI (P5) -----------------
AI_POLL_TASKS = {"explain", "purpose"}


@bp.route("/ai/<task>/<tx_id>")
@login_required
def ai_poll(task, tx_id):
    """UI polling for background AI jobs. Tenant-scoped through the same lookup as the receipt."""
    from ..ai import jobs
    from ..db import get_db
    from .payments import get_visible_tx

    if task not in AI_POLL_TASKS:
        abort(404)
    get_visible_tx(tx_id)  # 404 for another tenant's transaction
    job = jobs.get(get_db(), task, tx_id)
    if job is None:
        return jsonify({"status": "NONE"})
    return jsonify({"status": job["status"], "result": job["result"] if job["status"] == "DONE" else None})
