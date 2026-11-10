"""Configuration for CrossPay. Every value comes from the environment (see .env.example).

Config classes: DevConfig, TestConfig, ProdConfig, DemoConfig. Select one with
create_app("dev" | "test" | "prod" | "demo") or the CROSSPAY_ENV variable.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE = os.path.join(ROOT, "instance")


def _flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class BaseConfig:
    ENV_NAME = "base"
    TESTING = False

    SECRET_KEY = os.getenv("SECRET_KEY", "")
    DB_PATH = os.getenv("DB_PATH", os.path.join(INSTANCE, "crosspay.db"))
    LEDGER_PATH = os.getenv("LEDGER_PATH", os.path.join(INSTANCE, "blockchain_ledger.json"))
    MODEL_PATH = os.getenv("MODEL_PATH", os.path.join(ROOT, "model", "random_forest_model.pkl"))
    METRICS_PATH = os.getenv("METRICS_PATH", os.path.join(ROOT, "model", "metrics.json"))
    MODEL_CARD_PATH = os.getenv("MODEL_CARD_PATH", os.path.join(ROOT, "model", "model_card.json"))
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(INSTANCE, "uploads"))
    DEMO_MODE = _flag("DEMO_MODE", "0")
    FLASK_DEBUG = _flag("FLASK_DEBUG", "0")

    DEMO_SME_PASSWORD = os.getenv("DEMO_SME_PASSWORD", "")
    DEMO_ADMIN_PASSWORD = os.getenv("DEMO_ADMIN_PASSWORD", "")

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    MAX_CONTENT_LENGTH = 6 * 1024 * 1024

    # Policy thresholds on the 0-100 risk score (P3)
    REVIEW_AT = _float("REVIEW_AT", 40.0)
    BLOCK_AT = _float("BLOCK_AT", 80.0)
    LEDGER_SIGNING_KEY = os.getenv("LEDGER_SIGNING_KEY", "")
    POW_DIFFICULTY = _int("POW_DIFFICULTY", 3)
    EXCHANGE_RATE_MAX_STALE_HOURS = _float("EXCHANGE_RATE_MAX_STALE_HOURS", 24.0)
    INVOICE_REQUIRED_ABOVE_USD = _float("INVOICE_REQUIRED_ABOVE_USD", 50000.0)

    # Advisory LLM layer (P5+). Off unless LLM_ENABLED=1.
    LLM_ENABLED = _flag("LLM_ENABLED", "0")
    LLM_PROVIDERS = os.getenv("LLM_PROVIDERS", "groq,cloudflare,nvidia")
    LLM_TIMEOUT = _float("LLM_TIMEOUT", 15.0)
    LLM_DAILY_BUDGET_USD = _float("LLM_DAILY_BUDGET_USD", 1.0)
    LLM_LOG_RETENTION_DAYS = _int("LLM_LOG_RETENTION_DAYS", 30)
    AI_RATE_LIMIT = os.getenv("AI_RATE_LIMIT", "30 per hour")
    AI_FLAGS = {
        name: _flag(name, "1")
        for name in ("AI_EXPLAIN", "AI_PURPOSE", "AI_COPILOT", "AI_INVOICE", "AI_NLQ", "AI_ASSIST", "AI_REPORTS")
    }
    AI_RUN_SYNC = _flag("AI_RUN_SYNC", "0")  # tests run background jobs inline
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_ENABLED = True
    TRUSTED_PROXIES = [p.strip() for p in os.getenv("TRUSTED_PROXIES", "").split(",") if p.strip()]


class DevConfig(BaseConfig):
    ENV_NAME = "dev"


class DemoConfig(BaseConfig):
    ENV_NAME = "demo"
    DEMO_MODE = True


class ProdConfig(BaseConfig):
    ENV_NAME = "prod"
    SESSION_COOKIE_SECURE = True


class TestConfig(BaseConfig):
    ENV_NAME = "test"
    TESTING = True
    SECRET_KEY = "test-only-secret-key-not-for-production"
    LEDGER_SIGNING_KEY = "test-only-ledger-signing-key"
    DEMO_MODE = True
    LLM_ENABLED = False
    AI_RUN_SYNC = True
    POW_DIFFICULTY = 2
    DEMO_SME_PASSWORD = "sme-demo-password-test"
    DEMO_ADMIN_PASSWORD = "admin-demo-password-test"
    RATELIMIT_ENABLED = False


CONFIGS = {"dev": DevConfig, "demo": DemoConfig, "prod": ProdConfig, "test": TestConfig}
