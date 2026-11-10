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
    chain = current_app.extensions["blockchain"]
    is_valid, msg = chain.is_chain_valid()
    return jsonify({"valid": is_valid, "message": msg, "total_blocks": len(chain.chain)})


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
