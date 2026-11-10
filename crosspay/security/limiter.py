"""Rate limiting for AI endpoints, chat and uploads (G17, LLM06).

Client-IP logic adapted from Aegis Node (sandysunny99/aegis-node @4e64429, MIT) backend/limiter.py —
CF-Connecting-IP / X-Forwarded-For are honoured only when the direct peer is in TRUSTED_PROXIES (exact IPs or CIDR);
otherwise any client could spoof them. Logged-in users are limited per user id, anonymous requests per IP.
"""
import ipaddress

from flask import current_app, request, session
from flask_limiter import Limiter


def _trusted(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    for entry in current_app.config.get("TRUSTED_PROXIES", []):
        try:
            if ip in ipaddress.ip_network(entry, strict=False):
                return True
        except ValueError:
            continue
    return False


def client_ip() -> str:
    direct = request.remote_addr or "unknown"
    if _trusted(direct):
        cf = request.headers.get("CF-Connecting-IP", "").strip()
        if cf:
            return cf
        fwd = request.headers.get("X-Forwarded-For", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return direct


def limit_key() -> str:
    uid = session.get("user_id")
    return f"user:{uid}" if uid else f"ip:{client_ip()}"


limiter = Limiter(key_func=limit_key, default_limits=[], headers_enabled=True)


def ai_limit() -> str:
    return current_app.config.get("AI_RATE_LIMIT", "30 per hour")
