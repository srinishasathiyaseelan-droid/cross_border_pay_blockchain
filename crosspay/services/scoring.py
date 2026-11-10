"""Deterministic risk scoring (H1, M2, M5).

score(features) -> {level, p_low, p_med, p_high, score, engine, top_factors}

- engine "model": the Random Forest. level = most probable class; score = round((p_med*0.5 + p_high)*100, 1).
  Nothing is overwritten: if level and score look inconsistent both are shown as they are.
- engine "fallback": transparent rule points, used only when the model could not be loaded or failed its checks.
  Probabilities are None (never invented).
- top_factors: the three largest per-feature contributions to the risk score, from a tree-path decomposition
  (the treeinterpreter method, implemented here to avoid an extra dependency). Contributions are in score points.
The same input always gives the same output.
"""
import hashlib
import json
import logging
import os

import numpy as np
import pandas as pd

from .features import FEATURE_NAMES

log = logging.getLogger(__name__)
LEVELS = ["LOW", "MEDIUM", "HIGH"]
FEATURE_LABELS = {
    "amount": "Payment amount (USD)",
    "frequency": "Payments in the last 30 days",
    "previous_transactions": "Previous payments",
    "suspicious_transactions": "Prior held or blocked payments",
    "account_age": "Account age (months)",
    "corridor_risk": "Corridor risk",
    "amount_to_age_ratio": "Amount relative to account age",
}


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_bundle(model_path: str, card_path: str):
    """M2: verify the checksum BEFORE unpickling (a swapped file never executes), then the sklearn version and
    feature names. Returns (bundle | None, reason | None)."""
    import sklearn

    if not os.path.exists(model_path):
        return None, f"model file not found: {os.path.basename(model_path)}"
    try:
        with open(card_path, encoding="utf-8") as f:
            card = json.load(f)
    except (OSError, ValueError):
        return None, "model_card.json missing or unreadable"
    if _sha256(model_path) != card.get("sha256"):
        return None, "model checksum does not match model_card.json (file changed or swapped)"
    if card.get("sklearn_version") != sklearn.__version__:
        return None, (f"model trained with scikit-learn {card.get('sklearn_version')}, "
                      f"running {sklearn.__version__}; retrain or pin the version")
    try:
        import joblib

        bundle = joblib.load(model_path)
    except Exception as exc:  # noqa: BLE001
        return None, f"model failed to load: {type(exc).__name__}"
    if list(bundle.get("feature_names", [])) != FEATURE_NAMES or card.get("feature_names") != FEATURE_NAMES:
        return None, "model feature names do not match the feature builder"
    bundle["card"] = card
    return bundle, None


class Scorer:
    def __init__(self, bundle=None, fallback_reason: str = None):
        self.bundle = bundle if bundle and "model" in bundle else None
        self.fallback_reason = None if self.bundle else (fallback_reason or "model not loaded")
        if self.fallback_reason:
            log.warning("Risk scoring uses the FALLBACK engine: %s", self.fallback_reason)

    @property
    def engine(self) -> str:
        return "model" if self.bundle else "fallback"

    def score(self, features: dict) -> dict:
        if self.bundle is None:
            return self._fallback(features)
        model = self.bundle["model"]
        X = pd.DataFrame([[features[n] for n in FEATURE_NAMES]], columns=FEATURE_NAMES)
        proba = model.predict_proba(X)[0]
        p = {int(c): float(v) for c, v in zip(model.classes_, proba)}
        p_low, p_med, p_high = p.get(0, 0.0), p.get(1, 0.0), p.get(2, 0.0)
        level = LEVELS[max(range(3), key=lambda i: (p.get(i, 0.0), -i))]
        return {
            "level": level,
            "p_low": round(p_low, 4),
            "p_med": round(p_med, 4),
            "p_high": round(p_high, 4),
            "score": round((p_med * 0.5 + p_high) * 100, 1),
            "engine": "model",
            "top_factors": self.top_factors(X, features),
        }

    def contributions(self, X) -> tuple:
        """Tree-path decomposition: proba = bias + sum(contributions). Returns (bias[3], contrib[n_features, 3])."""
        model = self.bundle["model"]
        n_classes = len(model.classes_)
        bias = np.zeros(n_classes)
        contrib = np.zeros((len(FEATURE_NAMES), n_classes))
        x = X.to_numpy(dtype=np.float32)
        for est in model.estimators_:
            tree = est.tree_
            values = tree.value[:, 0, :]
            values = values / values.sum(axis=1, keepdims=True)
            path = est.decision_path(x).indices  # node ids, increasing = root to leaf
            bias += values[path[0]]
            for parent, child in zip(path[:-1], path[1:]):
                contrib[tree.feature[parent]] += values[child] - values[parent]
        n = len(model.estimators_)
        return bias / n, contrib / n

    def top_factors(self, X, features: dict, k: int = 3) -> list:
        _, contrib = self.contributions(X)
        score_pts = (contrib[:, 1] * 0.5 + contrib[:, 2]) * 100  # contribution to the 0-100 risk score
        order = np.argsort(-np.abs(score_pts))[:k]
        return [{"feature": FEATURE_NAMES[i], "label": FEATURE_LABELS[FEATURE_NAMES[i]],
                 "value": features[FEATURE_NAMES[i]], "contribution": round(float(score_pts[i]), 2)}
                for i in order]

    @staticmethod
    def _fallback(f: dict) -> dict:
        points, reasons = 0, []
        rules = [
            (f["amount"] > 50000, 45, "amount", "amount over 50,000 USD"),
            (15000 < f["amount"] <= 50000, 25, "amount", "amount 15,000-50,000 USD"),
            (f["suspicious_transactions"] >= 2, 35, "suspicious_transactions", "2+ prior held/blocked payments"),
            (f["suspicious_transactions"] == 1, 15, "suspicious_transactions", "1 prior held/blocked payment"),
            (f["corridor_risk"] >= 0.6, 25, "corridor_risk", "high-risk corridor"),
            (0.35 <= f["corridor_risk"] < 0.6, 10, "corridor_risk", "medium-risk corridor"),
            (f["account_age"] < 3, 10, "account_age", "account younger than 3 months"),
            (f["frequency"] >= 10, 10, "frequency", "10+ payments in 30 days"),
        ]
        for hit, pts, feat, why in rules:
            if hit:
                points += pts
                reasons.append({"feature": feat, "label": why, "value": f[feat], "contribution": float(pts)})
        score = float(min(100, points))
        level = "HIGH" if score >= 80 else "MEDIUM" if score >= 40 else "LOW"
        return {"level": level, "p_low": None, "p_med": None, "p_high": None, "score": score,
                "engine": "fallback", "top_factors": sorted(reasons, key=lambda r: -r["contribution"])[:3]}
