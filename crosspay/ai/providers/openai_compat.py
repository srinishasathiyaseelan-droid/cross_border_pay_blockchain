"""OpenAI-compatible chat-completions providers (Groq, NVIDIA NIM).

Adapted from Netvrio (sandysunny99/razorpay-ai-risk-manager @98bbc09) backend/llm/providers/openai_compat.py,
groq.py, nvidia.py — endpoints fixed in code, key and model ALWAYS from env (no hard-coded default model), errors
raised as ProviderError codes, raw text returned to the CrossPay guard instead of being parsed here.
"""
import os

import httpx

from ..errors import ProviderError
from .base import Completion, LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    url = ""
    key_env = ""
    model_env = ""
    json_mode = True

    def __init__(self):
        self.api_key = os.getenv(self.key_env, "").strip()
        self.model = os.getenv(self.model_env, "").strip()

    def is_configured(self) -> bool:
        return bool(self.api_key and self.model)

    def _body(self, system, user, max_tokens):
        body = {"model": self.model, "temperature": 0,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if "gpt-oss" in self.model:  # reasoning model: keep reasoning short and leave room for the answer
            body["reasoning_effort"] = "low"
            body["max_tokens"] = max_tokens + 512
        else:
            body["max_tokens"] = max_tokens
        if self.json_mode:
            body["response_format"] = {"type": "json_object"}
        return body

    def complete(self, system, user, *, max_tokens, timeout) -> Completion:
        if not self.is_configured():
            raise ProviderError("MISCONFIGURED")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(self.url, headers=headers, json=self._body(system, user, max_tokens))
        resp.raise_for_status()
        data = resp.json()
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise ProviderError("MALFORMED_RESPONSE", retryable=True)
        usage = data.get("usage") or {}
        return Completion(text, self.model, int(usage.get("prompt_tokens") or 0),
                          int(usage.get("completion_tokens") or 0))


class GroqProvider(OpenAICompatibleProvider):
    name = "groq"
    url = "https://api.groq.com/openai/v1/chat/completions"
    key_env = "GROQ_API_KEY"
    model_env = "GROQ_MODEL"


class NvidiaProvider(OpenAICompatibleProvider):
    name = "nvidia"
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    key_env = "NVIDIA_API_KEY"
    model_env = "NVIDIA_MODEL"
    json_mode = False  # not every NIM model accepts response_format; the prompt demands JSON
