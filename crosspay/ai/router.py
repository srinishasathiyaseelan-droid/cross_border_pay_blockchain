"""Priority-ordered provider router with retry and circuit breaker. Never raises to the caller.

Adapted from Netvrio (sandysunny99/razorpay-ai-risk-manager @98bbc09) backend/llm/router.py — synchronous for
Flask; dead "Test 1" try/pass block removed; failure_reason stores an error CODE (from crosspay.ai.errors), never
raw exception text (which can leak URLs or keys); one retry on a schema failure; a circuit breaker skips a provider
for CIRCUIT_COOLDOWN_S after CIRCUIT_THRESHOLD consecutive failures.
"""
import threading
import time
from typing import List, Optional, Tuple, Type

from pydantic import BaseModel

from .errors import SchemaError, classify
from .providers.base import LLMProvider

CIRCUIT_THRESHOLD = 3
CIRCUIT_COOLDOWN_S = 60.0


class Router:
    def __init__(self, providers: List[LLMProvider], timeout: float = 15.0, clock=time.monotonic):
        self.providers = providers
        self.timeout = timeout
        self._clock = clock
        self._lock = threading.Lock()
        self._failures = {p.name: 0 for p in providers}
        self._open_until = {p.name: 0.0 for p in providers}

    def circuit_state(self) -> dict:
        now = self._clock()
        with self._lock:
            return {p.name: {"failures": self._failures[p.name],
                             "open": self._open_until[p.name] > now,
                             "configured": p.is_configured(), "model": p.model or None}
                    for p in self.providers}

    def _record(self, name: str, ok: bool) -> None:
        with self._lock:
            if ok:
                self._failures[name] = 0
                self._open_until[name] = 0.0
            else:
                self._failures[name] += 1
                if self._failures[name] >= CIRCUIT_THRESHOLD:
                    self._open_until[name] = self._clock() + CIRCUIT_COOLDOWN_S

    def run(self, system: str, user: str, schema: Type[BaseModel], max_tokens: int,
            timeout: Optional[float] = None) -> Tuple[Optional[BaseModel], dict]:
        meta = {"provider": None, "model": None, "status": "UNAVAILABLE", "error_code": "NO_PROVIDER",
                "fallback_used": False, "attempts": 0, "latency_ms": 0, "input_tokens": 0, "output_tokens": 0,
                "raw_text": None}
        start = self._clock()
        tried = 0
        for provider in self.providers:
            if not provider.is_configured():
                continue
            with self._lock:
                if self._open_until[provider.name] > self._clock():
                    meta["error_code"] = "CIRCUIT_OPEN"
                    continue
            if tried:
                meta["fallback_used"] = True
            tried += 1
            for attempt in range(2):  # one retry, only for schema failures
                meta["attempts"] += 1
                try:
                    result, comp = provider.complete_json(system, user, schema, max_tokens=max_tokens,
                                                          timeout=timeout or self.timeout)
                except Exception as exc:  # noqa: BLE001 — classified into a code, never re-raised
                    c = classify(exc)
                    meta["error_code"] = f"{provider.name.upper()}:{c.code}"
                    if isinstance(exc, SchemaError) and attempt == 0:
                        continue
                    self._record(provider.name, ok=False)
                    break
                self._record(provider.name, ok=True)
                meta.update(provider=provider.name, model=comp.model, status="SUCCESS", error_code=None,
                            input_tokens=comp.input_tokens, output_tokens=comp.output_tokens, raw_text=comp.text,
                            latency_ms=int((self._clock() - start) * 1000))
                return result, meta
        meta["latency_ms"] = int((self._clock() - start) * 1000)
        return None, meta
