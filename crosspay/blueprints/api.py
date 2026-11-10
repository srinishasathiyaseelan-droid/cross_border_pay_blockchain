"""JSON API used by the UI."""
from urllib.parse import urlparse

from flask import Blueprint, abort, current_app, jsonify, request

from ..security.decorators import admin_required, demo_only, login_required

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


# ----------------- Live decision feed (Server-Sent Events) -----------------
def _feed_scope():
    from ..security.decorators import current_user_row
    from ..realtime import ADMIN

    row = current_user_row()
    return ADMIN if row["role"] == "admin" else row["id"]


@bp.route("/live/events")
@login_required
def live_events():
    """One long-lived SSE connection per open dashboard. SMEs get only their own payments (H3)."""
    from flask import Response

    from ..realtime import stream

    bus = current_app.extensions["events"]
    q = bus.subscribe(_feed_scope())  # subscribe before responding, so nothing published meanwhile is lost
    max_events = request.args.get("max", type=int) if current_app.config.get("TESTING") else None
    return Response(stream(bus, q, max_events=max_events), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@bp.route("/live/snapshot")
@login_required
def live_snapshot():
    from ..security.decorators import is_admin

    sim = current_app.extensions["simulator"]
    show_sim = is_admin() and current_app.config.get("DEMO_MODE")
    return jsonify({"events": current_app.extensions["events"].recent(_feed_scope(), 50),
                    "simulator": sim.status() if show_sim else None})


@bp.route("/live/stats")
@admin_required
def live_stats():
    """Live console KPIs. Counts come from the database (real payments only); p95 is the server-measured pipeline
    latency of recent decisions, real and simulated reported separately."""
    from ..db import get_db

    rows = dict(get_db().execute("SELECT decision, COUNT(*) FROM transactions GROUP BY decision").fetchall())
    decided = sum(v for k, v in rows.items() if k in ("APPROVED", "HOLD", "BLOCKED", "REJECTED"))
    bus = current_app.extensions["events"]
    p95, n = bus.latency_p95(False)
    sim_p95, sim_n = bus.latency_p95(True)
    return jsonify({
        "hold": rows.get("HOLD", 0), "blocked": rows.get("BLOCKED", 0), "rejected": rows.get("REJECTED", 0),
        "approved": rows.get("APPROVED", 0), "decided": decided,
        "approval_rate": round(rows.get("APPROVED", 0) / decided * 100, 1) if decided else None,
        "p95_ms": p95, "p95_samples": n, "sim_p95_ms": sim_p95, "sim_p95_samples": sim_n,
    })


@bp.route("/live/simulator", methods=["POST"])
@demo_only
@admin_required
def live_simulator():
    """DEMO_MODE + admin only. Dry run: synthetic payments are scored and decided, never stored."""
    body = request.get_json(silent=True) or {}
    sim = current_app.extensions["simulator"]
    try:
        sim.configure(body.get("rate_per_sec"), body.get("risky_ratio"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "rate_per_sec and risky_ratio must be numbers"}), 400
    if body.get("running") is True:
        sim.start()
    elif body.get("running") is False:
        sim.stop()
    return jsonify({"success": True, **sim.status()})
