"""Provider error classification.

Adapted from Aegis Node (sandysunny99/aegis-node @4e64429, MIT) backend/services/llm_error_classifier.py —
same categories and Retry-After clamp (60 s); returns an error CODE only (never raw exception text, which can
contain URLs or keys) so the router can store it safely.
"""
import calendar
import email.utils
import time
from dataclasses import dataclass
from typing import Optional

import httpx


class ProviderError(Exception):
    def __init__(self, code: str, retryable: bool = False, http_status: Optional[int] = None):
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.http_status = http_status


class SchemaError(Exception):
    """The provider answered but the answer was not valid JSON for the task schema."""


@dataclass
class Classified:
    code: str
    retryable: bool
    retry_after: Optional[int] = None
    http_status: Optional[int] = None


def parse_retry_after(value: Optional[str], max_delay: int = 60) -> Optional[int]:
    if not value or not value.strip():
        return None
    try:
        return min(max(0, int(value.strip())), max_delay)
    except ValueError:
        pass
    parsed = email.utils.parsedate(value)
    if parsed:
        return min(max(0, int(calendar.timegm(parsed) - time.time())), max_delay)
    return None


def classify(exc: Exception) -> Classified:
    if isinstance(exc, ProviderError):
        return Classified(exc.code, exc.retryable, None, exc.http_status)
    if isinstance(exc, httpx.HTTPStatusError):
        st = exc.response.status_code
        ra = parse_retry_after(exc.response.headers.get("retry-after"))
        if st == 429:
            return Classified("RATE_LIMITED", True, ra, st)
        if st == 401:
            return Classified("AUTHENTICATION_ERROR", False, None, st)
        if st == 403:
            return Classified("AUTHORIZATION_ERROR", False, None, st)
        if st in (400, 422):
            return Classified("BAD_REQUEST", False, None, st)
        if st in (404, 410):
            return Classified("MODEL_UNAVAILABLE", False, None, st)
        if st == 413:
            return Classified("CONTEXT_LIMIT", False, None, st)
        if st == 408:
            return Classified("TIMEOUT", True, ra, st)
        if st >= 500:
            return Classified("SERVER_ERROR", True, ra, st)
        return Classified("UNKNOWN_PROVIDER_ERROR", False, None, st)
    if isinstance(exc, httpx.TimeoutException):
        return Classified("TIMEOUT", True)
    if isinstance(exc, httpx.NetworkError):
        return Classified("NETWORK_ERROR", True)
    if isinstance(exc, SchemaError):
        return Classified("SCHEMA_ERROR", True)
    return Classified("UNKNOWN_PROVIDER_ERROR", False)
