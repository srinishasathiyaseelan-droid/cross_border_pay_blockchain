"""Deterministic fake provider used by every test (no network).

Script it with FakeLLMClient.script(task, response) where response is a dict (returned as JSON), a str (returned
as-is), an Exception instance (raised), or a callable(system, user) -> str|dict. Unscripted tasks get a minimal
valid default answer. Every call is recorded in .calls for assertions.
"""
import json

from .base import Completion, LLMProvider


class FakeLLMClient(LLMProvider):
    name = "fake"

    def __init__(self, model: str = "fake-model-1"):
        self.model = model
        self.calls = []
        self._scripts = {}
        self.default = None

    def script(self, task: str, response):
        self._scripts[task] = response
        return self

    def is_configured(self) -> bool:
        return True

    def complete(self, system, user, *, max_tokens, timeout) -> Completion:
        task = _task_from(system)
        self.calls.append({"task": task, "system": system, "user": user, "max_tokens": max_tokens})
        resp = self._scripts.get(task, self.default)
        if resp is None:
            resp = DEFAULTS.get(task, {})
        if callable(resp):
            resp = resp(system, user)
        if isinstance(resp, Exception):
            raise resp
        text = resp if isinstance(resp, str) else json.dumps(resp)
        return Completion(text, self.model, len(system + user) // 4, len(text) // 4)


def _task_from(system: str) -> str:
    for line in system.splitlines():
        if line.startswith("TASK:"):
            return line.split(":", 1)[1].strip()
    return "unknown"


DEFAULTS = {
    "explain": {"summary": "The model rated this payment using the evidence listed.", "factors": [],
                "what_would_lower_risk": [], "confidence_note": "Advisory only."},
    "purpose": {"category": "goods", "red_flags": [], "purpose_risk": 0.1, "rationale": "Trade goods."},
    "copilot": {"case_summary": "Case summary.", "checklist": [], "risk_for": [], "risk_against": [],
                "draft_memo": "Draft memo for the officer to edit."},
    "invoice": {"invoice_no": None, "issue_date": None, "seller": None, "buyer": None, "seller_country": None,
                "buyer_country": None, "currency": None, "total_amount": None, "line_items": [],
                "payment_terms": None, "confidence": {}},
    "nl_filter": {},
    "assistant": {"answer": "I can only answer questions about your own payment.", "refused": False,
                  "cited_evidence_ids": []},
    "report": {"title": "Draft", "body": "Draft report.", "key_points": []},
}
