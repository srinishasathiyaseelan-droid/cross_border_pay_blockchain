"""Task response schemas and the request forbidden-key check.

Adapted from Netvrio (sandysunny99/razorpay-ai-risk-manager @98bbc09) backend/llm/schemas.py — one response model
per task with extra="forbid"; NO recommended_action / verdict / decision field anywhere (G11): the copilot returns
checks and considerations, never a verdict. FORBIDDEN_KEYS extended for CrossPay PII; the hard-coded test-card
string check is replaced by the DLP engine (G12).
"""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

FORBIDDEN_KEYS = {
    "card_pan", "pan", "cvv", "pin", "api_key", "secret", "password", "token", "jwt", "authorization",
    "government_id", "email", "address", "phone", "account_number", "iban", "swift", "secret_key",
    "ledger_signing_key", "review_at", "block_at", "threshold", "thresholds",
}


class ForbiddenKeyError(ValueError):
    pass


def check_forbidden_keys(data: Any, path: str = "") -> None:
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(k, str) and k.lower() in FORBIDDEN_KEYS:
                raise ForbiddenKeyError(f"forbidden key {path}{k}")
            check_forbidden_keys(v, f"{path}{k}.")
    elif isinstance(data, list):
        for item in data:
            check_forbidden_keys(item, path)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _cap_list(n: int):
    def v(cls, value):
        return value[:n] if isinstance(value, list) else value
    return v


# ---- P6.1 risk explainer ----------------------------------------------------------------------------------
class FactorOut(_Strict):
    evidence_id: str = Field(..., max_length=40)
    plain_reason: str = Field(..., max_length=400)


class ExplainOut(_Strict):
    summary: str = Field(..., max_length=600)
    factors: List[FactorOut] = Field(default_factory=list, max_length=6)
    what_would_lower_risk: List[str] = Field(default_factory=list, max_length=3)
    confidence_note: str = Field("", max_length=300)

    @field_validator("summary")
    @classmethod
    def max_60_words(cls, v):
        if len(v.split()) > 60:
            raise ValueError("summary over 60 words")
        return v


# ---- P6.2 purpose tagger ----------------------------------------------------------------------------------
PURPOSE_CATEGORIES = ["goods", "services", "software", "freight", "consulting", "royalties", "loan_repayment",
                      "investment", "personal", "other"]
RED_FLAGS = ["offshore_consulting", "no_invoice", "urgent_secrecy", "crypto_conversion", "third_party_payment",
             "structuring_hint", "shell_company_hint", "sanctioned_goods_hint", "gift_or_donation", "cash_like"]


class PurposeOut(_Strict):
    category: Literal["goods", "services", "software", "freight", "consulting", "royalties", "loan_repayment",
                      "investment", "personal", "other"]
    red_flags: List[Literal["offshore_consulting", "no_invoice", "urgent_secrecy", "crypto_conversion",
                            "third_party_payment", "structuring_hint", "shell_company_hint", "sanctioned_goods_hint",
                            "gift_or_donation", "cash_like"]] = Field(default_factory=list, max_length=10)
    purpose_risk: float = Field(..., ge=0.0, le=1.0)
    rationale: str = Field("", max_length=300)

    @field_validator("rationale")
    @classmethod
    def max_30_words(cls, v):
        if len(v.split()) > 30:
            raise ValueError("rationale over 30 words")
        return v


# ---- P6.3 HOLD copilot ------------------------------------------------------------------------------------
class ChecklistItem(_Strict):
    item: str = Field(..., max_length=300)
    kind: Literal["document", "check"]


class PointOut(_Strict):
    point: str = Field(..., max_length=400)
    evidence_id: str = Field(..., max_length=40)


class CopilotOut(_Strict):
    case_summary: str = Field(..., max_length=1200)
    checklist: List[ChecklistItem] = Field(default_factory=list, max_length=10)
    risk_for: List[PointOut] = Field(default_factory=list, max_length=8)
    risk_against: List[PointOut] = Field(default_factory=list, max_length=8)
    draft_memo: str = Field(..., max_length=1200)


# ---- P6.4 invoice reader ----------------------------------------------------------------------------------
class LineItem(_Strict):
    description: str = Field(..., max_length=200)
    quantity: Optional[float] = None
    amount: Optional[float] = None


class InvoiceOut(_Strict):
    invoice_no: Optional[str] = Field(None, max_length=60)
    issue_date: Optional[str] = Field(None, max_length=20)
    seller: Optional[str] = Field(None, max_length=120)
    buyer: Optional[str] = Field(None, max_length=120)
    seller_country: Optional[str] = Field(None, max_length=60)
    buyer_country: Optional[str] = Field(None, max_length=60)
    currency: Optional[str] = Field(None, max_length=3)
    total_amount: Optional[float] = Field(None, ge=0)
    line_items: List[LineItem] = Field(default_factory=list, max_length=20)
    payment_terms: Optional[str] = Field(None, max_length=120)
    confidence: Dict[str, float] = Field(default_factory=dict)

    @field_validator("confidence")
    @classmethod
    def bounded(cls, v):
        return {k[:40]: max(0.0, min(1.0, float(x))) for k, x in list(v.items())[:12]}


# ---- P6.5 natural-language filter (no tenant or user field: G5) -------------------------------------------
class NLFilterOut(_Strict):
    decision: Optional[Literal["APPROVED", "HOLD", "BLOCKED", "REJECTED"]] = None
    risk_level: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = None
    receiver_country: Optional[str] = Field(None, max_length=40)
    currency: Optional[str] = Field(None, max_length=3)
    min_amount_usd: Optional[float] = Field(None, ge=0)
    max_amount_usd: Optional[float] = Field(None, ge=0)
    date_from: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    date_to: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    text: Optional[str] = Field(None, max_length=60)


# ---- P6.6 SME assistant -----------------------------------------------------------------------------------
class AssistantOut(_Strict):
    answer: str = Field(..., max_length=900)
    refused: bool = False
    cited_evidence_ids: List[str] = Field(default_factory=list, max_length=8)


# ---- P6.7 report drafts -----------------------------------------------------------------------------------
class ReportOut(_Strict):
    title: str = Field(..., max_length=160)
    body: str = Field(..., max_length=4000)
    key_points: List[str] = Field(default_factory=list, max_length=8)
