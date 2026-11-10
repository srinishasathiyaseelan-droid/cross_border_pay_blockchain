"""P6 AI feature endpoints. Every one goes through crosspay.ai.tasks -> pipeline.run_task (no direct provider use),
is rate limited (G17), tenant-scoped (G4, G5) and advisory. Pages render AI text with autoescape only."""
import json
import os
import secrets

from flask import Blueprint, abort, current_app, jsonify, request, session

from ..ai import tasks
from ..db import get_db, utcnow_iso
from ..security.decorators import login_required
from ..security.limiter import ai_limit, limiter
from ..services.features import ALLOWED_COUNTRIES
from .payments import get_visible_tx

bp = Blueprint("ai_features", __name__, url_prefix="/api/ai")

MAX_UPLOAD = 5 * 1024 * 1024


@bp.route("/assistant/<tx_id>", methods=["POST"])
@login_required
@limiter.limit(ai_limit)
def assistant(tx_id):
    """P6.6 SME help assistant: context is ONLY the caller's own record (tenant check) + a static FAQ."""
    tx = dict(get_visible_tx(tx_id))
    msg = ((request.get_json(silent=True) or {}).get("message") or "").strip()
    if not msg:
        return jsonify({"error": "Type a question."}), 400
    out = tasks.assistant(get_db(), tx, msg[:1000], session["user_id"])
    if out["status"] in ("OK", "REFUSED", "CHAT_LIMIT"):
        return jsonify({"answer": out["answer"], "refused": out.get("refused", False), "status": out["status"]})
    return jsonify({"answer": None, "status": out["status"],
                    "error": "The assistant could not answer safely. Your receipt above has the facts."})


@bp.route("/explain/<tx_id>", methods=["POST"])
@login_required
@limiter.limit(ai_limit)
def explain(tx_id):
    """"Explain with AI": (re)queue the advisory explanation for one visible payment. Tenant-scoped (G4)."""
    from ..ai.budget import ai_enabled

    get_visible_tx(tx_id)  # 404 for another tenant's payment
    conn = get_db()
    if not (ai_enabled(conn) and current_app.config.get("AI_FLAGS", {}).get("AI_EXPLAIN", True)):
        return jsonify({"status": "DISABLED", "error": "AI explanations are switched off."}), 503
    conn.execute("DELETE FROM ai_jobs WHERE task = 'explain' AND tx_id = ? AND status != 'PENDING'", (tx_id,))
    return jsonify({"status": tasks.queue_explanation(conn, tx_id)})


NL_KEYS = ("decision", "risk_level", "receiver_country", "currency", "min_amount_usd", "max_amount_usd", "date_from",
           "date_to", "text")


@bp.route("/nl_filter", methods=["POST"])
@login_required
@limiter.limit(ai_limit)
def nl_filter():
    """P6.5: natural language -> validated JSON filter (never SQL). The page applies it to the tenant-scoped query."""
    from urllib.parse import urlencode

    q = ((request.get_json(silent=True) or {}).get("query") or "").strip()
    if not q:
        return jsonify({"success": False, "error": "Describe what to find."}), 400
    res = tasks.nl_filter(get_db(), q[:300], session["user_id"])
    if not res.ok:
        return jsonify({"success": False, "status": res.status,
                        "error": "Could not turn that into a safe filter. Use the buttons and search box instead."})
    f = {k: v for k, v in res.data.items() if v not in (None, "")}
    if f.get("receiver_country") and f["receiver_country"] not in ALLOWED_COUNTRIES:
        f.pop("receiver_country")
    params = {"status": f.pop("decision", "ALL")}
    params.update({k: v for k, v in f.items() if k in NL_KEYS})
    return jsonify({"success": True, "filter": params, "query_string": urlencode(params)})


# ---- P6.4 invoice reader ------------------------------------------------------------------------------------
@bp.route("/invoice", methods=["POST"])
@login_required
@limiter.limit(ai_limit)
def extract_invoice():
    up = request.files.get("invoice")
    if up is None or not up.filename:
        return jsonify({"success": False, "error": "Choose a PDF invoice."}), 400
    head = up.stream.read(5)
    up.stream.seek(0)
    if head != b"%PDF-" or up.mimetype not in ("application/pdf", "application/x-pdf", "application/octet-stream"):
        return jsonify({"success": False, "error": "Only PDF invoices are supported."}), 415
    data = up.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        return jsonify({"success": False, "error": "The file is larger than 5 MB."}), 413
    os.makedirs(current_app.config["UPLOAD_DIR"], exist_ok=True)  # outside static/: never served
    token = secrets.token_hex(16)
    path = os.path.join(current_app.config["UPLOAD_DIR"], f"{token}.pdf")
    with open(path, "wb") as f:
        f.write(data)
    try:
        text, _meta = tasks.extract_pdf_text(path)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception:  # noqa: BLE001
        return jsonify({"success": False, "error": "The PDF could not be read."}), 400
    if not text.strip():
        return jsonify({"success": False, "error": "No text found (scanned images are not supported yet)."}), 400
    conn = get_db()
    result = tasks.read_invoice(conn, text, session["user_id"])
    conn.execute("INSERT INTO invoice_uploads (token, user_id, path, deterministic_json, fields_json, verification_json, "
                 "status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 (token, session["user_id"], path, json.dumps(result["deterministic"]),
                  json.dumps(result["fields"]), json.dumps(result["verification"]), result["status"], utcnow_iso()))
    return jsonify({"success": True, "token": token, "status": result["status"], "fields": result["fields"],
                    "deterministic": result["deterministic"], "verification": result["verification"]})


def invoice_for(conn, token: str, user_id: int):
    if not token:
        return None
    row = conn.execute("SELECT deterministic_json, fields_json, verification_json FROM invoice_uploads "
                       "WHERE token = ? AND user_id = ?", (token, user_id)).fetchone()
    if row is None:
        return None
    return {"deterministic": json.loads(row[0] or "{}"), "fields": json.loads(row[1] or "null"),
            "verification": json.loads(row[2] or "{}")}


@bp.before_request
def _same_origin():
    """Exempt from token CSRF (JSON/multipart API), so unsafe methods must come from this origin (H4)."""
    from urllib.parse import urlparse

    if request.method in ("GET", "HEAD", "OPTIONS"):
        return None
    origin = request.headers.get("Origin") or request.headers.get("Referer")
    if not origin or urlparse(origin).netloc != request.host:
        abort(403)
    if not (request.is_json or request.mimetype == "multipart/form-data"):
        abort(415)
    return None
