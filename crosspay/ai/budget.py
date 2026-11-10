"""Daily spend cap and runtime kill switch (LLM06).

Once today's estimated spend (UTC) reaches LLM_DAILY_BUDGET_USD, calls return UNAVAILABLE until midnight UTC.
The kill switch on /admin/ai (ai_settings.kill_switch) turns every AI call off at runtime without a restart;
LLM_ENABLED=0 turns it off at startup.
"""
from flask import current_app

from .log import spend_today


def ai_enabled(conn) -> bool:
    if not current_app.config.get("LLM_ENABLED"):
        return False
    row = conn.execute("SELECT value FROM ai_settings WHERE key = 'kill_switch'").fetchone()
    return not (row and row[0] == "1")


def set_kill_switch(conn, on: bool) -> None:
    conn.execute("INSERT OR REPLACE INTO ai_settings (key, value) VALUES ('kill_switch', ?)", ("1" if on else "0",))


def over_budget(conn) -> bool:
    return spend_today(conn) >= float(current_app.config.get("LLM_DAILY_BUDGET_USD", 0.0))


def estimate_cost(provider: str, input_tokens: int, output_tokens: int) -> float:
    from .providers.base import price_per_million

    pin, pout = price_per_million(provider or "", "in"), price_per_million(provider or "", "out")
    if pin is None or pout is None:
        return 0.0
    return (input_tokens * pin + output_tokens * pout) / 1_000_000
