"""Provider registry. LLM_PROVIDERS sets the fallback order; providers without credentials are skipped."""
from .cloudflare import CloudflareProvider
from .fake import FakeLLMClient
from .openai_compat import GroqProvider, NvidiaProvider

REGISTRY = {"groq": GroqProvider, "nvidia": NvidiaProvider, "cloudflare": CloudflareProvider}


def build(order: str) -> list:
    names = [n.strip().lower() for n in (order or "").split(",") if n.strip()]
    return [REGISTRY[n]() for n in dict.fromkeys(names) if n in REGISTRY]


__all__ = ["REGISTRY", "build", "FakeLLMClient", "GroqProvider", "NvidiaProvider", "CloudflareProvider"]
