"""Output guard: every model answer is untrusted (LLM05/07/10, G6, G7, G8, G10, G11).

Adapted from Netvrio (sandysunny99/razorpay-ai-risk-manager @98bbc09) backend/llm/policy.py (evidence-citation
check; null-safe now — Netvrio crashed when explanation was None) and Aegis Node (sandysunny99/aegis-node
@4e64429, MIT) backend/services/llm_service.py (_extract_first_json_object, 4,000-char cap, dangerous-pattern
rejection, per-field HTML/control-character stripping, list caps). Added: number/ID faithfulness (Aegis's
documented "unsupported claims" gap), URL/Markdown-image stripping, decision-word check, DLP redaction.

check() returns (clean_dict | None, code). code is "OK" or a REJECTED_GUARD reason.
"""
import json
import re
from typing import Iterable, Optional, Tuple

from ..security import dlp

MAX_RAW = 4000
MAX_FIELD = 1200
MAX_LIST = 10

_HTML_TAG = re.compile(r"<[^>]{0,200}>")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK = re.compile(r"\[([^\]]{0,200})\]\((?:https?|ftp|data|javascript):[^)]*\)", re.IGNORECASE)
_URL = re.compile(r"\b(?:https?|ftp)://\S+|\bwww\.\S+|\bdata:[a-z]+/[a-z0-9.+-]+[;,]\S*|\bjavascript:\S+", re.IGNORECASE)
_TRIPWIRE = re.compile(
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions|disregard\s+(the\s+)?system\s+prompt|system\s+override|"
    r"<\s*/?\s*user_data|BEGIN SYSTEM PROMPT|as an ai (language model|without restrictions)|developer mode|"
    r"rm\s+-rf|drop\s+table|os\.system|subprocess|__import__|eval\s*\(|exec\s*\(", re.IGNORECASE)
_NUMBER = re.compile(r"(?<![A-Za-z_])[-+]?\d[\d,]*(?:\.\d+)?\s*[kKmM]?(?![\w])")
_IDS = re.compile(r"\bTX-[0-9A-Za-z-]{4,40}\b|\bev_[0-9a-z]+_\d+\b")
# Outcome verbs per decision family. A bare mention ("not yet settled", "two prior blocked payments") is neutral;
# only a CLAIM or RECOMMENDATION built around one of these verbs is rejected (see decision_claims()).
DECISION_VERBS = {
    "APPROVED": r"(?:approv\w*|releas\w*|authori[sz]\w*|clear(?:ed|s|ing)?|settl\w*)",
    "BLOCKED": r"(?:block(?:ed|ing|s)?)",
    "REJECTED": r"(?:reject\w*|declin\w*)",
}
# Base forms only, so nouns at the start of a sentence ("Settlement is pending") are not read as orders.
IMPERATIVES = {
    DECISION_VERBS["APPROVED"]: "approve|release|authori[sz]e|clear|settle|green-?light",
    DECISION_VERBS["BLOCKED"]: "block",
    DECISION_VERBS["REJECTED"]: "reject|decline",
}
_SUBJECT = r"(?:payment|transaction|transfer|funds|it|this|case)"
_AUX = r"(?:is|was|are|were|has\s+been|have\s+been|had\s+been|will\s+be|would\s+be|gets|got|being|be)"
_ADV = r"(?:\s+(?:now|already|fully|then|therefore|safely|immediately|automatically|likely|probably|definitely))?"


def _claim_patterns(verb: str) -> list:
    """Shapes that state or recommend an outcome, case-insensitive unless noted."""
    i = re.IGNORECASE
    return [
        # "should be approved", "will be blocked", "can be released", "must reject", "to release the funds"
        re.compile(rf"\b(?:should|must|ought\s+to|can|could|may|might|will|would|shall|to|let'?s)\s+(?:not\s+)?"
                   rf"(?:now\s+|safely\s+|simply\s+|just\s+)?(?:be\s+)?{verb}\b", i),
        # "recommend we release", "I suggest approving", "advise blocking", "in favour of release"
        re.compile(rf"\b(?:recommend\w*|suggest\w*|advis\w*|propos\w*|favou?r\w*|endorse\w*|urge\w*)\b"
                   rf"(?:\s+\S+){{0,4}}?\s+{verb}\b", i),
        # "this payment is approved", "the transfer has been released", "it is now cleared"
        # (a negated subject such as "No funds have been released" is a neutral statement of fact)
        re.compile(rf"(?<!\bno\s)(?<!\bnot\s)\b{_SUBJECT}\s+{_AUX}{_ADV}\s+{verb}\b", i),
        # "I approve", "we would release", "officer will reject"
        re.compile(rf"\b(?:i|we|you|officer|officers|compliance)\s+(?:would\s+|will\s+|can\s+|should\s+)?{verb}\b", i),
        # imperative at the start of a sentence: "Approve, risk is low." / "Release the payment."
        re.compile(rf"(?:^|[.!?;:\n]\s*)(?:{IMPERATIVES[verb]})\b", i | re.MULTILINE),
    ]


# Verdict labels written in capitals ("APPROVE, risk is low", "Status: BLOCKED") are claims even without a verb frame.
VERDICT_LABELS = {
    "APPROVED": re.compile(r"\b(?:APPROVE|APPROVED|RELEASE|RELEASED|AUTHORISED|AUTHORIZED|CLEARED|SETTLED)\b"
                           r"|(?i:\bgreen[- ]?(?:light\w*|lit)\b)"),
    "BLOCKED": re.compile(r"\b(?:BLOCK|BLOCKED)\b"),
    "REJECTED": re.compile(r"\b(?:REJECT|REJECTED|DECLINE|DECLINED)\b"),
}
DECISION_CLAIMS = {d: _claim_patterns(v) + [VERDICT_LABELS[d]] for d, v in DECISION_VERBS.items()}


def decision_claims(text: str, stored_decision: str) -> list:
    """Decisions (other than the stored one) that the text claims or recommends."""
    found = []
    for decision, patterns in DECISION_CLAIMS.items():
        if decision == stored_decision:
            continue
        if any(p.search(text or "") for p in patterns):
            found.append(decision)
    return found


def extract_first_json_object(text: str) -> Optional[str]:
    """Stack-based: the first complete {...}, ignoring trailing (possibly injected) text."""
    text = (text or "")[:MAX_RAW * 4]
    start = text.find("{")
    if start == -1:
        return None
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def clean_text(s: str) -> Tuple[str, bool]:
    """Strip Markdown images/links, URLs, HTML and control characters; cap length. -> (text, stripped_any)."""
    orig = s
    s = _MD_IMAGE.sub("", s)
    s = _MD_LINK.sub(r"\1", s)
    s = _URL.sub("[link removed]", s)
    s = _HTML_TAG.sub("", s)
    s = _CONTROL.sub("", s)
    s = s.strip()[:MAX_FIELD]
    return s, s != orig.strip()[:MAX_FIELD]


def _walk_strings(obj, fn):
    if isinstance(obj, dict):
        return {k: _walk_strings(v, fn) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_walk_strings(v, fn) for v in obj[:MAX_LIST]]
    if isinstance(obj, str):
        return fn(obj)
    return obj


def _strings(obj) -> Iterable[str]:
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)
    elif isinstance(obj, str):
        yield obj


def _num(token: str) -> Optional[float]:
    t = token.strip().replace(",", "")
    mult = 1.0
    if t[-1:] in "kK":
        mult, t = 1e3, t[:-1]
    elif t[-1:] in "mM":
        mult, t = 1e6, t[:-1]
    try:
        return float(t) * mult
    except ValueError:
        return None


def numbers_in(text: str) -> list:
    out = []
    for m in _NUMBER.finditer(text or ""):
        tok = m.group(0)
        v = _num(tok)
        if v is not None:
            decimals = len(tok.split(".")[1].rstrip("kKmM ")) if "." in tok else 0
            out.append((tok.strip(), v, decimals))
    return out


def unsupported_numbers(output_text: str, context_text: str) -> list:
    """G6: every number in the output must match a number in the input (allowing the output to round it)."""
    ctx = [v for _, v, _ in numbers_in(context_text)]
    ctx_pct = ctx + [v * 100 for v in ctx if abs(v) <= 1]  # 0.42 in context may be written as 42%
    bad = []
    for tok, v, d in numbers_in(output_text):
        ok = any(abs(round(c, d) - v) < 1e-9 or abs(c - v) < 1e-9 or (d == 0 and abs(round(c) - v) < 1e-9)
                 for c in ctx_pct)
        if not ok:
            bad.append(tok)
    return bad


def unsupported_ids(output_text: str, context_text: str) -> list:
    ctx = set(_IDS.findall(context_text or ""))
    return [i for i in _IDS.findall(output_text or "") if i not in ctx]


def check(model_obj, *, valid_evidence_ids: Iterable[str] = (), context_text: str = "",
          stored_decision: Optional[str] = None, faithfulness: bool = True, decision_words: bool = True,
          raw_text: Optional[str] = None) -> Tuple[Optional[dict], str, list]:
    """-> (clean dict | None, code, events)"""
    events = []
    if model_obj is None:
        return None, "NO_OUTPUT", events
    if raw_text and len(raw_text) > MAX_RAW * 4:
        return None, "REJECTED_GUARD:TOO_LONG", events
    data = model_obj.model_dump() if hasattr(model_obj, "model_dump") else dict(model_obj)

    # 1. tripwire over every text field (G10) — case-insensitive
    for s in _strings(data):
        if _TRIPWIRE.search(s):
            return None, "REJECTED_GUARD:INJECTION_TRIPWIRE", events

    # 2. citations: every cited evidence id must exist
    valid = set(valid_evidence_ids or ())
    cited = [x.get("evidence_id") for k in ("factors", "risk_for", "risk_against") for x in data.get(k, []) or []]
    cited += list(data.get("cited_evidence_ids", []) or [])
    if any(c not in valid for c in cited if c is not None):
        return None, "REJECTED_GUARD:UNKNOWN_EVIDENCE_ID", events

    # 3. strip links/images/HTML, cap lengths (G7)
    stripped = {"any": False}

    def _clean(s):
        c, changed = clean_text(s)
        stripped["any"] |= changed
        return c

    data = _walk_strings(data, _clean)
    if stripped["any"]:
        events.append("STRIPPED_MARKUP_OR_URL")

    all_text = "\n".join(_strings(data))
    # 4. numbers and IDs must appear in the input (G6)
    if faithfulness:
        if unsupported_ids(all_text, context_text):
            return None, "REJECTED_GUARD:UNSUPPORTED_ID", events
        if unsupported_numbers(all_text, context_text):
            return None, "REJECTED_GUARD:UNSUPPORTED_NUMBER", events

    # 5. no claim of a decision that is not the stored one (LLM07, G11)
    if decision_words and stored_decision:
        try:
            if decision_claims(all_text, stored_decision):
                return None, "REJECTED_GUARD:DECISION_CLAIM", events
        except Exception:  # noqa: BLE001 — fail closed
            return None, "REJECTED_GUARD:DECISION_CLAIM", events

    # 6. DLP on the output: redact before storing or showing (G8)
    try:
        if dlp.scan(all_text):
            data = dlp.sanitize(data)
            events.append("OUTPUT_REDACTED")
    except Exception:  # noqa: BLE001 — fail closed
        return None, "REJECTED_GUARD:DLP_ERROR", events
    return json.loads(json.dumps(data)), "OK", events
