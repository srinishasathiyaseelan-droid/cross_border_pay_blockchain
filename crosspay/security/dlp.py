"""Data-loss prevention for every LLM payload and response, and for logs (LLM02, G8, G12, G16).

Adapted from Netvrio (sandysunny99/razorpay-ai-risk-manager @98bbc09) backend/app/security/dlp.py — kept the
Luhn-checked card, JWT, API-key, DB-URI and private-key detectors; added US EIN, India PAN/GSTIN, IBAN, SWIFT/BIC,
email, phone and LLM-provider key shapes (Groq gsk_, NVIDIA nvapi-, Bearer tokens); replaced Netvrio's hard-coded
"41112222" test-card string. scan() never raises on odd input; callers treat any exception as a block (fail closed).
"""
import re
from typing import Any, Dict, List

PAN_CANDIDATE = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")
JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
BEARER = re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]{12,}=*", re.IGNORECASE)
API_KEY = re.compile(r"\b(?:rzp|cf|sk|pk)_(?:live|test)_[A-Za-z0-9]{10,64}\b|\bgsk_[A-Za-z0-9]{20,}\b|"
                     r"\bnvapi-[A-Za-z0-9_-]{20,}\b|\bsk-[A-Za-z0-9_-]{20,}\b|\bhf_[A-Za-z0-9]{20,}\b|\bAIza[0-9A-Za-z_-]{30,}\b")
DB_URI = re.compile(r"\b(?:sqlite|postgres(?:ql)?|mysql|mongodb(?:\+srv)?)(?:\+[a-z0-9]+)?://[^\s\"']+", re.IGNORECASE)
PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
HEX_PRIVATE_KEY = re.compile(r"\b0x[a-fA-F0-9]{64}\b")
US_EIN = re.compile(r"\b\d{2}-\d{7}\b|\bEIN[\s:#-]*\d{9}\b|\bUS-EIN-\d{9}\b", re.IGNORECASE)
IN_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
IN_GSTIN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")
IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}(?:[ ]?[A-Z0-9]{1,4})?\b")
SWIFT = re.compile(r"\b(?:SWIFT|BIC)[\s:#-]*[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b", re.IGNORECASE)
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE = re.compile(r"(?<![\w.])\+?\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}(?![\w.])")

RULES = [
    ("JWT", JWT), ("BEARER_TOKEN", BEARER), ("API_KEY", API_KEY), ("DB_URI", DB_URI), ("PRIVATE_KEY", PRIVATE_KEY),
    ("HEX_PRIVATE_KEY", HEX_PRIVATE_KEY), ("US_EIN", US_EIN), ("IN_GSTIN", IN_GSTIN), ("IN_PAN", IN_PAN),
    ("IBAN", IBAN), ("SWIFT_BIC", SWIFT), ("EMAIL", EMAIL), ("PHONE", PHONE),
]


def luhn_valid(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def _flatten(data: Any) -> str:
    if isinstance(data, dict):
        return " ".join(f"{k} {_flatten(v)}" for k, v in data.items())
    if isinstance(data, (list, tuple)):
        return " ".join(_flatten(v) for v in data)
    return "" if data is None else str(data)


def scan(data: Any) -> List[Dict[str, str]]:
    """Violations found in a string or nested structure. Samples are always masked."""
    text = _flatten(data)
    found = []
    for m in PAN_CANDIDATE.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and luhn_valid(digits):
            found.append({"type": "CARD_PAN", "sample": "****" + digits[-4:]})
    for name, rx in RULES:
        if rx.search(text):
            found.append({"type": name, "sample": f"[{name}]"})
    return found


def redact(text: Any) -> str:
    s = "" if text is None else str(text)

    def _pan(m):
        digits = re.sub(r"\D", "", m.group(0))
        return "[CARD_PAN]" if 13 <= len(digits) <= 19 and luhn_valid(digits) else m.group(0)

    s = PAN_CANDIDATE.sub(_pan, s)
    for name, rx in RULES:
        s = rx.sub(f"[{name}]", s)
    return s


def sanitize(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: sanitize(v) for k, v in data.items()}
    if isinstance(data, list):
        return [sanitize(v) for v in data]
    if isinstance(data, str):
        return redact(data)
    return data
