"""Cloudflare Workers AI.

Adapted from Netvrio (sandysunny99/razorpay-ai-risk-manager @98bbc09) backend/llm/providers/cloudflare.py —
model from CLOUDFLARE_MODEL only (Netvrio defaulted to an old 8B chat model), handles both the legacy
{"result": {"response": ...}} and the OpenAI-style result shapes, raises ProviderError codes.
"""
import json
import os

import httpx

from ..errors import ProviderError
from .base import Completion, LLMProvider


class CloudflareProvider(LLMProvider):
    name = "cloudflare"

    def __init__(self):
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
        self.token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
        self.model = os.getenv("CLOUDFLARE_MODEL", "").strip()

    def is_configured(self) -> bool:
        return bool(self.account_id and self.token and self.model)

    def complete(self, system, user, *, max_tokens, timeout) -> Completion:
        if not self.is_configured():
            raise ProviderError("MISCONFIGURED")
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/{self.model}"
        body = {"messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "max_tokens": max_tokens, "temperature": 0}
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers={"Authorization": f"Bearer {self.token}"}, json=body)
        resp.raise_for_status()
        data = resp.json()
        inner = data.get("result") if isinstance(data, dict) else None
        if isinstance(inner, dict) and "response" in inner:
            text = inner["response"]
        elif isinstance(inner, dict) and inner.get("choices"):
            text = inner["choices"][0]["message"]["content"]
        else:
            raise ProviderError("MALFORMED_RESPONSE", retryable=True)
        if isinstance(text, (dict, list)):
            text = json.dumps(text)
        usage = (inner or {}).get("usage") or {}
        return Completion(text or "", self.model, int(usage.get("prompt_tokens") or 0),
                          int(usage.get("completion_tokens") or 0))
