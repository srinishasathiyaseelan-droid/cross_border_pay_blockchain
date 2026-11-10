"""Deterministic risk scoring (H1, M5).

score(features) -> {level, p_low, p_med, p_high, score, engine, top_factors}

- engine "model": the Random Forest. level = most probable class; score = round((p_med*0.5 + p_high)*100, 1).
  Nothing is overwritten: if level and score look inconsistent both are shown as they are.
- engine "fallback": transparent rule points, used only when the model could not be loaded. Probabilities are
  None (never invented).
The same input always gives the same output.
"""
import logging

import pandas as pd

from .features import FEATURE_NAMES

log = logging.getLogger(__name__)
LEVELS = ["LOW", "MEDIUM", "HIGH"]


class Scorer:
    def __init__(self, bundle=None, fallback_reason: str = None):
        self.bundle = bundle if bundle and "model" in bundle else None
        self.fallback_reason = fallback_reason if self.bundle is None else None
        if self.bundle is None and not self.fallback_reason:
            self.fallback_reason = "model not loaded"

    @property
    def engine(self) -> str:
        return "model" if self.bundle else "fallback"

    def score(self, features: dict) -> dict:
        if self.bundle is None:
            return self._fallback(features)
        model = self.bundle["model"]
        names = self.bundle.get("feature_names", FEATURE_NAMES)
        X = pd.DataFrame([[features[n] for n in names]], columns=names)
        proba = model.predict_proba(X)[0]
        p = {int(c): float(v) for c, v in zip(model.classes_, proba)}
        p_low, p_med, p_high = p.get(0, 0.0), p.get(1, 0.0), p.get(2, 0.0)
        level = LEVELS[max(range(3), key=lambda i: (p.get(i, 0.0), -i))]
        out = {
            "level": level,
            "p_low": round(p_low, 4),
            "p_med": round(p_med, 4),
            "p_high": round(p_high, 4),
            "score": round((p_med * 0.5 + p_high) * 100, 1),
            "engine": "model",
            "top_factors": self.top_factors(X, features),
        }
        return out

    def top_factors(self, X, features: dict, k: int = 3) -> list:
        return []

    @staticmethod
    def _fallback(f: dict) -> dict:
        points, reasons = 0, []
        rules = [
            (f["amount"] > 50000, 45, "amount over 50,000 USD"),
            (15000 < f["amount"] <= 50000, 25, "amount 15,000-50,000 USD"),
            (f["suspicious_transactions"] >= 2, 35, "2+ prior held/blocked payments"),
            (f["suspicious_transactions"] == 1, 15, "1 prior held/blocked payment"),
            (f["corridor_risk"] >= 0.6, 25, "high-risk corridor"),
            (0.35 <= f["corridor_risk"] < 0.6, 10, "medium-risk corridor"),
            (f["account_age"] < 3, 10, "account younger than 3 months"),
            (f["frequency"] >= 10, 10, "10+ payments in 30 days"),
        ]
        for hit, pts, why in rules:
            if hit:
                points += pts
                reasons.append({"feature": why, "value": None, "contribution": pts / 100})
        score = float(min(100, points))
        level = "HIGH" if score >= 80 else "MEDIUM" if score >= 40 else "LOW"
        return {"level": level, "p_low": None, "p_med": None, "p_high": None, "score": score,
                "engine": "fallback", "top_factors": reasons[:3]}
