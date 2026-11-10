"""Input guard for every user-controlled string sent to an LLM (LLM01, G13, G14, G15, LLM06).

Adapted from Aegis Node (sandysunny99/aegis-node @4e64429, MIT) backend/services/guardrails.py — canonicalise
(NFKC, zero-width / bidi / Unicode-tag stripping), bounded base64 decoding and the signal families are kept.
Changes: payment-specific signals ("mark as low risk", "approve this payment", "skip review", "split into smaller
payments"), Hindi and Telugu phrasings, and the Aegis false positive where "override" + "rules" anywhere in the
text fired (e.g. "override shipping rules per contract") is removed: overrides must target instructions/risk/review.

This is a tripwire, not the defence (OWASP: injection cannot be reliably filtered). The defence is architectural:
no tools, no writes, escalate-only signals, output guard. A BLOCK here only skips the AI call and adds an evidence
item for the officer; it is NOT an escalation trigger unless the measured FPR on CrossPay's benign notes is <= 2%.
"""
import base64
import re
import string
import unicodedata

CAPS = {"notes": 500, "chat": 1000, "receiver": 120, "query": 300, "invoice_text": 12000, "default": 500}

_INVISIBLE = re.compile("[​-‏‪-‮⁠-⁤⁦-⁩﻿\U000e0000-\U000e007f]")
_BASE64 = re.compile(r"(?:[A-Za-z0-9+/]{4}){5,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?")
_CLOSING_TAG = re.compile(r"</\s*user_data\s*>", re.IGNORECASE)

SIGNALS = {
    "INSTRUCTION_OVERRIDE": (3, re.compile(
        r"ignore\s+(all\s+)?(the\s+)?(previous|prior|above|earlier)\s+(instructions|rules|prompts?|messages?)|"
        r"disregard\s+(all\s+)?(the\s+)?(prior|previous|above|system)\s+(rules|instructions|prompt)|"
        r"forget\s+(all\s+)?(your\s+|previous\s+)?instructions|override\s+(the\s+)?(system|safety|risk|compliance)\s+"
        r"(rules|instructions|policy|checks)|new\s+instructions\s*:|bypass\s+(the\s+)?(policy|guard|review|checks)",
        re.IGNORECASE)),
    "ROLE_IMPERSONATION": (3, re.compile(
        r"(^|\s)(system|assistant|developer)\s*:\s*\S|you\s+are\s+now\s+|act\s+as\s+(a|an|the)\s+|"
        r"pretend\s+(to\s+be|you\s+are)|<\s*/?\s*(system|assistant|user_data)\b|\[\s*(system|inst)\s*\]",
        re.IGNORECASE)),
    "PROMPT_EXTRACTION": (3, re.compile(
        r"(reveal|show|print|repeat|translate|output)\s+(me\s+)?(the\s+|your\s+)?(system\s+prompt|hidden\s+"
        r"instructions|instructions\s+above|thresholds?|internal\s+(rules|policy))|what\s+(is|are)\s+your\s+"
        r"(instructions|thresholds?)", re.IGNORECASE)),
    "DECISION_MANIPULATION": (3, re.compile(
        r"(mark|rate|classify|score|set|treat)\s+(this|it|the\s+payment|me)?\s*(as\s+)?(low|zero|no)[\s-]*risk|"
        r"approve\s+(this|the|my)\s+(payment|transfer|transaction)|auto[\s-]*approve|"
        r"skip\s+(the\s+)?(compliance\s+|manual\s+|aml\s+)?(review|check|verification)|"
        r"do\s+not\s+(flag|hold|block|review)|(release|clear)\s+(the\s+)?(hold|payment)\s+(now|immediately)|"
        r"risk[_\s]*(score|level)\s*[=:]\s*(0|low)", re.IGNORECASE)),
    "EVASION": (2, re.compile(
        r"split\s+(it\s+|this\s+|the\s+payment\s+)?(into|in)\s+(smaller|multiple|several)\s+(payments|transfers|parts)|"
        r"(stay|keep\s+it|remain)\s+(just\s+)?(under|below)\s+(the\s+)?(limit|threshold|radar)|"
        r"avoid\s+(the\s+)?(review|detection|reporting|aml)", re.IGNORECASE)),
    "SECRET_EXFILTRATION": (3, re.compile(
        r"(return|print|show|dump|reveal)\s+(the\s+)?(api\s+key|secret|password|credentials|environment\s+"
        r"variables|signing\s+key)|other\s+(users?|customers?|smes?)'?\s*(transactions|payments|data)",
        re.IGNORECASE)),
    "EXFIL_MARKUP": (2, re.compile(r"!\[[^\]]*\]\(\s*https?://|<img\b|https?://\S+\?(q|d|data|x)=", re.IGNORECASE)),
    "MULTILINGUAL_OVERRIDE": (3, re.compile(
        # Hindi: "pichhle nirdesh andekha karo", "ise kam jokhim mark karo", "is bhugtan ko manzoor karo"
        r"पिछले\s*(सभी\s*)?निर्देश|निर्देशों\s*को\s*(अनदेखा|नज़रअंदाज़|भूल)|कम\s*जोखिम|भुगतान\s*(को\s*)?(मंज़ूर|मंजूर|स्वीकृत)|"
        r"समीक्षा\s*(छोड़|मत)|"
        # Telugu: "mundu suchanalu pattinchukoku", "takkuva risk", "chellimpu aamodinchu"
        r"మునుపటి\s*సూచనలు|సూచనలను\s*(విస్మరించు|పట్టించుకోకు)|తక్కువ\s*(రిస్క్|ప్రమాదం)|చెల్లింపును?\s*ఆమోదించు|"
        r"సమీక్ష\s*(దాటవేయి|వద్దు)|"
        # romanised Hindi / Telugu
        r"\b(pichhle|pichle)\s+nirdesh|\bkam\s+jokhim\b|\bmanzoor\s+karo\b|\bsuchanalu\s+(pattinchukoku|vismarinchu)\b|"
        r"\btakkuva\s+risk\b", re.IGNORECASE)),
}


def canonicalize(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text))
    text = _INVISIBLE.sub("", text)
    text = "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch)[0] != "C")
    return re.sub(r"[ \t]+", " ", text).strip()


def _decoded_views(text: str) -> str:
    views = [text]
    for m in _BASE64.finditer(text):
        chunk = m.group(0)
        if len(chunk) > 2000:
            continue
        try:
            s = base64.b64decode(chunk + "===").decode("utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            continue
        if s and sum(c in string.printable for c in s) > 0.8 * len(s):
            views.append(canonicalize(s))
    rot = text.translate(str.maketrans("ABCDEFGHIJKLMabcdefghijklmNOPQRSTUVWXYZnopqrstuvwxyz",
                                       "NOPQRSTUVWXYZnopqrstuvwxyzABCDEFGHIJKLMabcdefghijklm"))
    views.append(rot)
    return "\n".join(views)


_TAG_CHARS = re.compile("[\U000e0000-\U000e007f]")
_BIDI = re.compile("[‪-‮⁦-⁩]")
# Common Cyrillic/Greek look-alikes folded to Latin for ANALYSIS only (the text sent on is not changed).
_CONFUSABLES = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d",
    "ӏ": "l", "к": "k", "м": "m", "т": "t", "в": "b", "н": "h", "А": "A", "Е": "E", "О": "O", "Р": "P", "С": "C",
    "Т": "T", "Х": "X", "Н": "H", "К": "K", "М": "M", "В": "B", "ο": "o", "α": "a", "ε": "e", "ρ": "p", "ι": "i",
    "κ": "k", "ν": "v", "τ": "t", "υ": "u", "Ο": "O", "Α": "A", "Ε": "E", "Ρ": "P", "Τ": "T",
})


def _despace(text: str) -> str:
    """'i g n o r e   p r e v i o u s' -> 'ignore previous' when most tokens are single characters."""
    tokens = text.split()
    if len(tokens) < 8 or sum(len(t) == 1 for t in tokens) < 0.6 * len(tokens):
        return text
    words = re.split(r"\s{2,}", text)
    return " ".join(w.replace(" ", "") for w in words)


def evaluate(text: str) -> dict:
    """-> {status: ALLOW|RESTRICT|BLOCK, score, signals}"""
    raw = "" if text is None else str(text)
    norm = canonicalize(raw)
    folded = norm.translate(_CONFUSABLES)
    spaced = _INVISIBLE.sub("", unicodedata.normalize("NFKC", raw)).translate(_CONFUSABLES)  # keep runs of spaces
    analysed = _decoded_views(folded) + "\n" + _despace(spaced)
    score, signals = 0, []
    for name, (weight, rx) in SIGNALS.items():
        if rx.search(analysed):
            score += weight
            signals.append(name)
    if _TAG_CHARS.search(raw):  # invisible Unicode tag characters have no place in a payment note
        score += 3
        signals.append("HIDDEN_UNICODE_TAGS")
    if _BIDI.search(raw):
        score += 2
        signals.append("BIDI_CONTROL")
    if _CLOSING_TAG.search(norm):
        score += 3
        signals.append("DELIMITER_BREAKOUT")
    status = "BLOCK" if score >= 3 else "RESTRICT" if score >= 2 else "ALLOW"
    return {"status": status, "score": score, "signals": signals}


def prepare(name: str, value: str, kind: str = "default") -> dict:
    """Normalise, cap, escape and wrap one user field. The wrapped text is what the model sees."""
    raw = "" if value is None else str(value)
    cap = CAPS.get(kind, CAPS["default"])
    norm = canonicalize(raw)
    truncated = len(norm) > cap
    norm = norm[:cap]
    verdict = evaluate(raw[: cap * 4])
    escaped = norm.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_name = re.sub(r"[^a-z_]", "", name.lower())[:30] or "field"
    return {
        "name": safe_name,
        "clean": norm,
        "wrapped": f'<user_data name="{safe_name}">{escaped}</user_data>',
        "truncated": truncated,
        "verdict": verdict,
    }
