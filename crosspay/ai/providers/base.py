"""Provider interface.

Adapted from Netvrio (sandysunny99/razorpay-ai-risk-manager @98bbc09) backend/llm/interfaces.py — synchronous,
task-agnostic: complete() returns raw text + token usage; complete_json() validates it against the task's Pydantic
schema. No tools, no function calling (LLM03): pure text in, JSON out.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Type

from pydantic import BaseModel, ValidationError

from ..errors import SchemaError


@dataclass
class Completion:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class LLMProvider(ABC):
    name: str = "base"
    model: str = ""

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def complete(self, system: str, user: str, *, max_tokens: int, timeout: float) -> Completion: ...

    def complete_json(self, system: str, user: str, schema: Type[BaseModel], *, max_tokens: int,
                      timeout: float) -> tuple:
        from ..guard import extract_first_json_object

        comp = self.complete(system, user, max_tokens=max_tokens, timeout=timeout)
        raw = extract_first_json_object(comp.text or "")
        if raw is None:
            raise SchemaError("no JSON object in response")
        try:
            return schema.model_validate_json(raw), comp
        except ValidationError as exc:
            raise SchemaError("schema validation failed") from exc

    def health(self) -> dict:
        return {"provider": self.name, "model": self.model or None, "configured": self.is_configured()}


def price_per_million(provider: str, kind: str) -> Optional[float]:
    import os

    defaults = {"groq": (0.15, 0.60), "cloudflare": (0.29, 2.25), "nvidia": (0.0, 0.0), "fake": (0.0, 0.0)}
    env = os.getenv(f"LLM_PRICE_{provider.upper()}_{'IN' if kind == 'in' else 'OUT'}")
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    pair = defaults.get(provider)
    return None if pair is None else pair[0 if kind == "in" else 1]
