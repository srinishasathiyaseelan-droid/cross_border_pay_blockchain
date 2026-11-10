"""429 handling: falls through to the next provider, never trips the breaker, honours a short Retry-After."""
import httpx

from crosspay.ai.providers import FakeLLMClient
from crosspay.ai.providers.base import LLMProvider
from crosspay.ai.router import CIRCUIT_THRESHOLD, Router
from crosspay.ai.schemas import PurposeOut

OK = {"category": "goods", "red_flags": [], "purpose_risk": 0.1, "rationale": "ok"}


class Limited(LLMProvider):
    name = "limited"
    model = "limited-1"

    def __init__(self, retry_after=None, succeed_after=None):
        self.calls, self.retry_after, self.succeed_after = 0, retry_after, succeed_after
        self.fake = FakeLLMClient().script("purpose", OK)

    def is_configured(self):
        return True

    def complete(self, system, user, *, max_tokens, timeout):
        self.calls += 1
        if self.succeed_after is not None and self.calls > self.succeed_after:
            return self.fake.complete(system, user, max_tokens=max_tokens, timeout=timeout)
        headers = {"retry-after": str(self.retry_after)} if self.retry_after is not None else {}
        req = httpx.Request("POST", "https://example.invalid")
        raise httpx.HTTPStatusError("429", request=req, response=httpx.Response(429, headers=headers, request=req))


def test_rate_limit_falls_through_and_never_opens_the_breaker():
    t = [0.0]
    lim, good = Limited(), FakeLLMClient().script("purpose", OK)
    r = Router([lim, good], clock=lambda: t[0], sleep=lambda s: None)
    for _ in range(CIRCUIT_THRESHOLD + 2):
        result, meta = r.run("TASK: purpose", "u", PurposeOut, 100)
        assert isinstance(result, PurposeOut) and meta["provider"] == "fake"
        t[0] += 30  # past the rate-limit cool-off each time
    st = r.circuit_state()["limited"]
    assert st["failures"] == 0 and not st["open"]


def test_rate_limited_provider_is_skipped_during_cooloff():
    t = [0.0]
    lim = Limited()
    r = Router([lim], clock=lambda: t[0], sleep=lambda s: None)
    _, meta = r.run("TASK: purpose", "u", PurposeOut, 100)
    assert meta["errors"] == ["LIMITED:RATE_LIMITED"] and lim.calls == 1
    _, meta = r.run("TASK: purpose", "u", PurposeOut, 100)
    assert lim.calls == 1 and meta["errors"] == ["LIMITED:RATE_LIMITED"]  # skipped, no call
    assert r.circuit_state()["limited"]["rate_limited"]


def test_short_retry_after_is_honoured_in_place():
    slept = []
    lim = Limited(retry_after=1, succeed_after=1)
    result, meta = Router([lim], sleep=slept.append).run("TASK: purpose", "u", PurposeOut, 100)
    assert isinstance(result, PurposeOut) and lim.calls == 2 and slept == [1]


def test_every_provider_reason_is_reported(app, db, fake_llm):
    from crosspay.ai.pipeline import run_task
    from crosspay.ai import context

    app.extensions["ai_router"] = Router([Limited()], sleep=lambda s: None)
    with app.app_context():
        res = run_task("purpose", context.purpose("Invoice 4471 for parts", "India to Germany", 1000.0), None, db)
    assert res.status == "UNAVAILABLE" and res.meta["errors"] == ["LIMITED:RATE_LIMITED"]
    row = db.execute("SELECT guard_outcome FROM llm_calls ORDER BY id DESC LIMIT 1").fetchone()
    assert row[0] == "LIMITED:RATE_LIMITED"


def test_selftest_shows_the_reason(app, admin_client, db, fake_llm):
    app.extensions["ai_router"] = Router([Limited()], sleep=lambda s: None)
    page = admin_client.post("/admin/ai", data={"action": "selftest"}).text
    assert "UNAVAILABLE" in page and "LIMITED:RATE_LIMITED" in page


def test_retry_after_parsing_accepts_fractions_and_durations():
    from crosspay.ai.errors import parse_retry_after

    assert parse_retry_after("7.2") == 8 and parse_retry_after("697ms") == 1 and parse_retry_after("2.5s") == 3
    assert parse_retry_after("5") == 5 and parse_retry_after("900") == 60 and parse_retry_after("soon") is None


def test_groq_token_window_header_is_used_when_retry_after_missing():
    from crosspay.ai.errors import classify

    req = httpx.Request("POST", "https://example.invalid")
    resp = httpx.Response(429, headers={"x-ratelimit-reset-tokens": "6.4s"}, request=req)
    assert classify(httpx.HTTPStatusError("429", request=req, response=resp)).retry_after == 7


def test_selftest_stops_before_the_request_timeout(app, db, fake_llm, monkeypatch):
    import time as _time

    from crosspay.ai import tasks

    t = [0.0]
    monkeypatch.setattr(_time, "monotonic", lambda: t.__setitem__(0, t[0] + 30) or t[0])
    with app.app_context():
        out = tasks.self_test(db, 1, delay=0)
    assert any(s == "SKIPPED" for _, s, _ in out) and len(out) == 7
