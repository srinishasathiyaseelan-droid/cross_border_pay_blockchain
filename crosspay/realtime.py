"""Live decision feed: an in-process event bus, Server-Sent Events and a demo-only traffic simulator.

Adapted from Netvrio (sandysunny99/razorpay-ai-risk-manager @1d41992, backend/realtime/bus.py, generator.py,
api/routes/live.py). What changed:
- Flask + threads instead of FastAPI + asyncio: subscribers are bounded ``queue.Queue`` objects.
- Tenant scoping follows CrossPay's rule (H3): an SME only receives events for its own payments; compliance
  admins receive every event.
- Events carry no names, notes or IDs other than the transaction ID; amounts are USD-normalised and rounded.
- The simulator is a DRY RUN. It draws synthetic behaviour vectors, scores them with the real Random Forest and
  decides them with the real policy engine, but it never writes to the database, the audit chain or the ledger,
  and it makes no FX or AI calls. Every simulated event is marked ``simulated: true`` and only admins see them.
"""
import itertools
import logging
import math
import queue
import random
import threading
import time
from collections import deque

log = logging.getLogger(__name__)

HISTORY_SIZE = 200
SUBSCRIBER_QUEUE_SIZE = 500
HEARTBEAT_SECONDS = 15.0
ADMIN = "admin"


class EventBus:
    """Thread-safe pub/sub. ``publish`` never blocks: a slow subscriber loses its oldest events."""

    def __init__(self, history_size: int = HISTORY_SIZE):
        self._lock = threading.Lock()
        self._history = deque(maxlen=history_size)
        self._subs = []  # (scope, queue): scope is ADMIN or an SME's user_id
        self._seq = itertools.count(1)

    @staticmethod
    def _visible(scope, event) -> bool:
        if scope == ADMIN:
            return True
        return not event.get("simulated") and event.get("user_id") == scope

    def publish(self, event: dict) -> dict:
        enriched = {**event, "seq": next(self._seq), "ts": int(time.time() * 1000)}
        with self._lock:
            self._history.append(enriched)
            subs = list(self._subs)
        for scope, q in subs:
            if not self._visible(scope, enriched):
                continue
            try:
                q.put_nowait(enriched)
            except queue.Full:
                try:
                    q.get_nowait()
                    q.put_nowait(enriched)
                except (queue.Empty, queue.Full):
                    pass
        return enriched

    def subscribe(self, scope) -> queue.Queue:
        q = queue.Queue(maxsize=SUBSCRIBER_QUEUE_SIZE)
        with self._lock:
            self._subs.append((scope, q))
        return q

    def unsubscribe(self, q) -> None:
        with self._lock:
            self._subs = [(s, x) for s, x in self._subs if x is not q]

    def recent(self, scope, limit: int = 50) -> list:
        with self._lock:
            items = [e for e in self._history if self._visible(scope, e)]
        return [public(e) for e in items[-limit:]]

    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subs)


def public(event: dict) -> dict:
    """What leaves the server: the internal user_id is dropped."""
    return {k: v for k, v in event.items() if k != "user_id"}


def settlement_event(kind: str, row: dict, decision: str, block=None) -> dict:
    usd = row.get("normalized_usd_amount")
    return {
        "type": kind,  # "decision" | "review"
        "tx_id": row.get("transaction_id"),
        "user_id": row.get("user_id"),
        "decision": decision,
        "risk_level": row.get("risk_level"),
        "risk_score": row.get("risk_score"),
        "amount_usd": round(float(usd), 2) if usd is not None else None,
        "corridor": f"{row.get('sender_country')} → {row.get('receiver_country')}",
        "engine": row.get("scoring_engine"),
        "block": block,
        "simulated": False,
    }


def publish_safely(app, event: dict) -> None:
    """Called after COMMIT. A feed failure must never affect a settlement."""
    try:
        app.extensions["events"].publish(event)
    except Exception:  # noqa: BLE001
        log.exception("Live feed publish failed (settlement already committed)")


def sse(event: dict) -> str:
    import json

    return f"id: {event['seq']}\nevent: {event['type']}\ndata: {json.dumps(public(event), separators=(',', ':'))}\n\n"


def stream(bus: EventBus, q: queue.Queue, heartbeat: float = HEARTBEAT_SECONDS, max_events: int = None):
    """SSE body. ``q`` is subscribed by the caller before the response starts, so nothing is missed."""
    sent = 0
    try:
        yield "retry: 3000\n\n"
        while max_events is None or sent < max_events:
            try:
                event = q.get(timeout=heartbeat)
            except queue.Empty:
                yield ": keep-alive\n\n"
                continue
            yield sse(event)
            sent += 1
    finally:
        bus.unsubscribe(q)


# --------------------------------------------------------------------------- demo traffic simulator (dry run)

SIM_PROFILES = {  # behaviour drawn around the three DEMO_VECTORS, with jitter
    "low": {"frequency": (1, 4), "previous_transactions": (20, 80), "suspicious_transactions": (0, 0), "account_age": (12, 48)},
    "medium": {"frequency": (3, 9), "previous_transactions": (5, 20), "suspicious_transactions": (0, 1), "account_age": (4, 14)},
    "high": {"frequency": (12, 25), "previous_transactions": (0, 3), "suspicious_transactions": (2, 6), "account_age": (1, 3)},
}
SIM_AMOUNT_USD = {"low": (3_000, 0.6), "medium": (25_000, 0.5), "high": (120_000, 0.5)}  # log-normal median, sigma


class TrafficSimulator:
    def __init__(self, app, rng: random.Random = None):
        self.app = app
        self.rng = rng or random.Random()
        self.rate_per_sec = 1.0
        self.risky_ratio = 0.35
        self.emitted = 0
        self._thread = None
        self._stop = threading.Event()
        self._lock = threading.Lock()

    def build(self) -> dict:
        from .services.features import ALLOWED_COUNTRIES, corridor_risk

        r = self.rng.random()
        profile = "low" if r >= self.risky_ratio else ("medium" if r >= self.risky_ratio / 3 else "high")
        median, sigma = SIM_AMOUNT_USD[profile]
        amount = round(min(500_000.0, max(100.0, median * math.exp(self.rng.gauss(0, sigma)))), 2)
        sender, receiver = self.rng.choice(ALLOWED_COUNTRIES), self.rng.choice(ALLOWED_COUNTRIES)
        features = {k: self.rng.randint(lo, hi) for k, (lo, hi) in SIM_PROFILES[profile].items()}
        features["amount"] = amount
        features["corridor_risk"] = corridor_risk(sender, receiver)
        features["amount_to_age_ratio"] = round(amount / (features["account_age"] + 0.5), 2)
        scored = self.app.extensions["scorer"].score(features)
        decision = self.app.extensions["contract"].decide("VERIFIED", scored["level"], scored["score"])
        return {
            "type": "decision",
            "tx_id": "SIM-" + "".join(self.rng.choice("0123456789ABCDEFGHJKMNPQRSTVWXYZ") for _ in range(10)),
            "decision": decision.decision,
            "risk_level": scored["level"],
            "risk_score": scored["score"],
            "amount_usd": amount,
            "corridor": f"{sender} → {receiver}",
            "engine": scored["engine"],
            "block": None,
            "simulated": True,
        }

    def emit_once(self) -> dict:
        event = self.app.extensions["events"].publish(self.build())
        with self._lock:
            self.emitted += 1
        return event

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.emit_once()
            except Exception:  # noqa: BLE001
                log.exception("Simulator event failed")
            interval = 1.0 / self.rate_per_sec
            self._stop.wait(max(0.05, self.rng.expovariate(1.0 / interval)))

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def configure(self, rate_per_sec=None, risky_ratio=None):
        if rate_per_sec is not None:
            self.rate_per_sec = min(10.0, max(0.2, float(rate_per_sec)))
        if risky_ratio is not None:
            self.risky_ratio = min(0.9, max(0.0, float(risky_ratio)))

    def start(self):
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="crosspay-sim", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def status(self) -> dict:
        return {"running": self.running, "rate_per_sec": self.rate_per_sec, "risky_ratio": self.risky_ratio,
                "emitted": self.emitted, "dry_run": True}
