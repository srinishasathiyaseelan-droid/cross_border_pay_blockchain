"""CrossPay: risk-adaptive cross-border settlement for SMEs (Flask application factory)."""
import json
import logging
import os

from dotenv import load_dotenv

load_dotenv(override=False)

from flask import Flask, render_template, session  # noqa: E402

from .config import CONFIGS, ROOT  # noqa: E402
from . import db as dbmod  # noqa: E402

log = logging.getLogger("crosspay")


def create_app(config_name: str = None, overrides: dict = None) -> Flask:
    config_name = config_name or os.getenv("CROSSPAY_ENV", "dev")
    app = Flask(
        __name__,
        template_folder=os.path.join(ROOT, "templates"),
        static_folder=os.path.join(ROOT, "static"),
    )
    app.config.from_object(CONFIGS[config_name])
    if overrides:
        app.config.update(overrides)

    if not app.config.get("SECRET_KEY"):
        if config_name == "prod":
            raise RuntimeError("SECRET_KEY must be set when CROSSPAY_ENV=prod")  # C3
        app.config["SECRET_KEY"] = _local_secret(app, "secret_key")
    if not app.config.get("LEDGER_SIGNING_KEY"):
        if config_name == "prod":
            raise RuntimeError("LEDGER_SIGNING_KEY must be set when CROSSPAY_ENV=prod")
        app.config["LEDGER_SIGNING_KEY"] = _local_secret(app, "ledger_signing_key")

    dbmod.init_db(app)
    app.teardown_appcontext(dbmod.close_db)
    from .security.pii import encrypt_legacy_rows

    conn = dbmod.connect(app.config["DB_PATH"])
    try:
        encrypt_legacy_rows(conn, app.config.get("KYC_ENCRYPTION_KEY") or app.config["SECRET_KEY"])
    finally:
        conn.close()

    from flask_wtf.csrf import CSRFProtect

    csrf = CSRFProtect(app)  # H4

    from .services.currency import CurrencyService
    from .ledger.chain import Blockchain, SmartContractEngine

    chain = Blockchain(app.config["LEDGER_PATH"], difficulty=2)
    app.extensions["currency"] = CurrencyService()
    app.extensions["blockchain"] = chain
    app.extensions["contract"] = SmartContractEngine(chain)
    app.extensions["model"] = _load_model(app)
    from .services.scoring import Scorer

    app.extensions["scorer"] = Scorer(app.extensions["model"])
    app.extensions["metrics"] = _load_metrics(app)

    from .blueprints import admin, api, auth, kyc, payments

    for bp in (auth.bp, kyc.bp, payments.bp, admin.bp, api.bp):
        app.register_blueprint(bp)
    # The JSON API is exempt from token CSRF but must pass a same-origin check on unsafe methods.
    csrf.exempt(api.bp)

    @app.context_processor
    def inject_global_data():
        from .services.currency import COUNTRY_TO_DEFAULT_CURRENCY, SUPPORTED_CURRENCIES

        user = kyc_info = None
        if "user_id" in session:
            conn = dbmod.get_db()
            row = conn.execute("SELECT id, name, email, role, created_at FROM users WHERE id = ?",
                               (session["user_id"],)).fetchone()
            krow = conn.execute(
                "SELECT id, status, business_name, country FROM kyc WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                (session["user_id"],),
            ).fetchone()
            user = dict(row) if row else None
            kyc_info = dict(krow) if krow else None
        return dict(
            current_user=user,
            current_kyc=kyc_info,
            is_admin=bool(user and user["role"] == "admin"),
            demo_mode=bool(app.config.get("DEMO_MODE")),
            metrics=app.extensions["metrics"],
            supported_currencies=SUPPORTED_CURRENCIES,
            country_currencies=COUNTRY_TO_DEFAULT_CURRENCY,
        )

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403, message="This action needs a compliance officer account."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, message="That page or record does not exist."), 404

    from flask_wtf.csrf import CSRFError

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        return render_template("error.html", code=400, message="The form expired or was not sent from this site. "
                               "Reload the page and try again."), 400

    return app


def _local_secret(app, name: str) -> str:
    """Dev/demo only: a random key persisted under instance/ so sessions survive restarts."""
    if app.config.get("TESTING"):
        return os.urandom(32).hex()
    path = os.path.join(os.path.dirname(os.path.abspath(app.config["DB_PATH"])), f".{name}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(os.urandom(32).hex())
        log.warning("%s not set: generated a local one in %s (never use this in production)", name.upper(), path)
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


_MODEL_CACHE = {}


def _load_model(app):
    path = app.config["MODEL_PATH"]
    if not os.path.exists(path):
        log.warning("Model file not found at %s; run python model/train_model.py", path)
        return None
    st = os.stat(path)
    key = (os.path.abspath(path), st.st_mtime_ns, st.st_size)
    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]
    try:
        import joblib

        _MODEL_CACHE[key] = joblib.load(path)
        return _MODEL_CACHE[key]
    except Exception as exc:  # noqa: BLE001
        log.error("Could not load model: %s", exc)
        return None


def _load_metrics(app):
    try:
        with open(app.config["METRICS_PATH"], encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}
