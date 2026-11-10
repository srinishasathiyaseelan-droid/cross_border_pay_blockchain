"""CrossPay Random Forest: synthetic data, training and honest evaluation (P4: M1, M2).

What changed from the original script (whose near-perfect accuracy came from drawing each class from its
own non-overlapping ranges):
- one population of SMEs; every feature drawn from overlapping distributions (log-normal amounts, Poisson counts);
- corridor risk computed from the real country table (crosspay.services.features);
- labels come from a noisy latent risk rule, then 7% label noise (flip to an adjacent class);
- every row has a created_at, and the split is by time: oldest 70% train, next 15% validation, newest 15% test;
- metrics: per-class precision/recall/F1 and PR-AUC, confusion matrix, 5-fold CV mean ± std, Brier score and a
  reliability table; a REVIEW_AT/BLOCK_AT sweep on validation; false negatives on test.
- the artefact records sklearn_version, feature_names, trained_at and a sha256 checksum (model_card.json).

The data is synthetic. The numbers measure how well the model recovers this generator's rule, not real-world fraud
detection performance.

Run:  python model/train_model.py
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import StratifiedKFold, cross_validate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from crosspay.policy import engine as policy  # noqa: E402
from crosspay.services.features import COUNTRY_RISK_MAP, FEATURE_NAMES, corridor_risk  # noqa: E402

SEED = 42
N_SAMPLES = 6000
LABEL_NOISE = 0.07
CLASSES = ["LOW", "MEDIUM", "HIGH"]
MODEL_DIR = os.path.join(ROOT, "model")
EVAL_DIR = os.path.join(MODEL_DIR, "evaluation")

SENDER_WEIGHTS = {"United States": 0.22, "United Kingdom": 0.12, "Germany": 0.12, "Singapore": 0.10, "Japan": 0.06,
                  "Canada": 0.06, "Australia": 0.06, "France": 0.06, "India": 0.12, "United Arab Emirates": 0.08}
RECEIVER_WEIGHTS = {c: w for c, w in {
    "United States": 0.10, "United Kingdom": 0.08, "Germany": 0.10, "Singapore": 0.07, "Japan": 0.05,
    "Canada": 0.05, "Australia": 0.05, "France": 0.05, "India": 0.11, "Brazil": 0.08, "United Arab Emirates": 0.07,
    "Mexico": 0.06, "South Africa": 0.04, "Nigeria": 0.04, "Russia": 0.02, "Pakistan": 0.03}.items()}


def _pick(rng, weights: dict, n: int) -> np.ndarray:
    keys = list(weights)
    p = np.array([weights[k] for k in keys], dtype=float)
    return rng.choice(keys, size=n, p=p / p.sum())


def generate_sme_dataset(n_samples: int = N_SAMPLES, random_state: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(random_state)
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    days = np.sort(rng.uniform(0, 668, n_samples))  # 2025-01-01 .. 2026-10-31
    created_at = [(start + timedelta(days=float(d))).replace(microsecond=0).isoformat().replace("+00:00", "Z")
                  for d in days]

    segment = rng.choice(["established", "growing", "new"], size=n_samples, p=[0.55, 0.30, 0.15])
    age = np.where(segment == "established", rng.integers(18, 121, n_samples),
                   np.where(segment == "growing", rng.integers(4, 25, n_samples), rng.integers(1, 7, n_samples)))
    previous = rng.poisson(age * rng.uniform(0.4, 2.5, n_samples))
    burst = rng.random(n_samples) < 0.08
    frequency = np.where(burst, rng.poisson(14, n_samples), rng.poisson(rng.lognormal(np.log(3), 0.6, n_samples)))
    risky = rng.random(n_samples) < 0.12
    suspicious = np.where(risky, rng.poisson(2.0, n_samples), rng.poisson(0.15, n_samples))
    senders = _pick(rng, SENDER_WEIGHTS, n_samples)
    receivers = _pick(rng, RECEIVER_WEIGHTS, n_samples)
    corridor = np.array([corridor_risk(s, r) for s, r in zip(senders, receivers)])
    amount = rng.lognormal(np.log(9000), 1.0, n_samples) * np.exp(0.5 * risky)
    amount = np.clip(amount, 50, 1_000_000).round(2)

    # Latent risk: a noisy rule over the same seven features the model sees.
    z = (0.75 * np.log(amount / 10000)
         + 4.0 * (corridor - 0.30)
         + 0.70 * np.minimum(suspicious, 5)
         + 0.90 * np.log10(1 + frequency)
         + 0.80 * (age < 4)
         - 0.20 * np.log1p(previous)
         + rng.normal(0, 0.6, n_samples))
    q60, q85 = np.quantile(z, [0.60, 0.85])
    labels = np.where(z < q60, 0, np.where(z < q85, 1, 2))
    flip = rng.random(n_samples) < LABEL_NOISE
    step = np.where(labels == 0, 1, np.where(labels == 2, -1, rng.choice([-1, 1], n_samples)))
    labels = np.where(flip, labels + step, labels)

    df = pd.DataFrame({
        "created_at": created_at,
        "sender_country": senders,
        "receiver_country": receivers,
        "amount": amount,
        "frequency": frequency.astype(int),
        "previous_transactions": previous.astype(int),
        "suspicious_transactions": suspicious.astype(int),
        "account_age": age.astype(int),
        "corridor_risk": corridor.round(3),
        "amount_to_age_ratio": (amount / (age + 0.5)).round(2),
        "risk_label": labels.astype(int),
        "label_source": "synthetic_rule_v2",
    })
    return df


def time_split(df: pd.DataFrame):
    df = df.sort_values("created_at").reset_index(drop=True)
    n = len(df)
    a, b = int(n * 0.70), int(n * 0.85)
    return df.iloc[:a], df.iloc[a:b], df.iloc[b:]


def build_model() -> RandomForestClassifier:
    return RandomForestClassifier(n_estimators=200, max_depth=10, min_samples_leaf=5, class_weight="balanced",
                                  random_state=SEED, n_jobs=1)


def risk_scores(proba: np.ndarray) -> np.ndarray:
    return np.round((proba[:, 1] * 0.5 + proba[:, 2]) * 100, 1)


def reliability_table(proba: np.ndarray, y: np.ndarray, bins: int = 10) -> list:
    conf = proba.max(axis=1)
    pred = proba.argmax(axis=1)
    edges = np.linspace(0, 1, bins + 1)
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi) if lo > 0 else (conf >= lo) & (conf <= hi)
        if m.sum() == 0:
            continue
        rows.append({"bin": f"{lo:.1f}-{hi:.1f}", "count": int(m.sum()),
                     "mean_confidence": round(float(conf[m].mean()), 4),
                     "accuracy": round(float((pred[m] == y[m]).mean()), 4)})
    return rows


def multiclass_brier(proba: np.ndarray, y: np.ndarray) -> float:
    onehot = np.eye(3)[y]
    return float(np.mean(np.sum((proba - onehot) ** 2, axis=1)))


def class_metrics(y: np.ndarray, proba: np.ndarray) -> dict:
    pred = proba.argmax(axis=1)
    p, r, f, s = precision_recall_fscore_support(y, pred, labels=[0, 1, 2], zero_division=0)
    out = {}
    for i, name in enumerate(CLASSES):
        out[name] = {"precision": round(float(p[i]), 4), "recall": round(float(r[i]), 4),
                     "f1": round(float(f[i]), 4), "support": int(s[i]),
                     "pr_auc": round(float(average_precision_score((y == i).astype(int), proba[:, i])), 4)}
    return out


def decisions(level_idx: np.ndarray, scores: np.ndarray, review_at: float, block_at: float) -> list:
    return [policy.evaluate("VERIFIED", CLASSES[i], s, review_at, block_at).decision
            for i, s in zip(level_idx, scores)]


def sweep(y: np.ndarray, proba: np.ndarray) -> pd.DataFrame:
    scores, level = risk_scores(proba), proba.argmax(axis=1)
    rows = []
    for review_at in range(20, 65, 5):
        for block_at in range(60, 100, 5):
            if block_at <= review_at:
                continue
            d = np.array(decisions(level, scores, review_at, block_at))
            hi, md, lo = y == 2, y == 1, y == 0
            rows.append({
                "review_at": review_at, "block_at": block_at,
                "high_blocked": round(float((d[hi] == "BLOCKED").mean()), 4),
                "high_approved": round(float((d[hi] == "APPROVED").mean()), 4),
                "medium_held_or_blocked": round(float((d[md] != "APPROVED").mean()), 4),
                "low_approved": round(float((d[lo] == "APPROVED").mean()), 4),
                "low_blocked": round(float((d[lo] == "BLOCKED").mean()), 4),
                "manual_review_share": round(float((d == "HOLD").mean()), 4),
            })
    return pd.DataFrame(rows)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def train_and_evaluate(write: bool = True, review_at: float = 40.0, block_at: float = 80.0) -> dict:
    df = generate_sme_dataset()
    train, val, test = time_split(df)
    X_tr, y_tr = train[FEATURE_NAMES], train["risk_label"].to_numpy()
    X_va, y_va = val[FEATURE_NAMES], val["risk_label"].to_numpy()
    X_te, y_te = test[FEATURE_NAMES], test["risk_label"].to_numpy()

    model = build_model().fit(X_tr, y_tr)
    p_va, p_te = model.predict_proba(X_va), model.predict_proba(X_te)
    pred_te = p_te.argmax(axis=1)

    cv = cross_validate(build_model(), X_tr, y_tr, cv=StratifiedKFold(5, shuffle=True, random_state=SEED),
                        scoring={"accuracy": "accuracy", "f1_macro": "f1_macro"})
    scores_te, level_te = risk_scores(p_te), pred_te
    d_te = np.array(decisions(level_te, scores_te, review_at, block_at))
    sweep_df = sweep(y_va, p_va)

    metrics = {
        "model_name": "Random Forest Classifier",
        "n_estimators": 200, "max_depth": 10, "min_samples_leaf": 5, "class_weight": "balanced",
        "random_state": SEED,
        "data": {"generator": "synthetic_rule_v2", "total_samples": int(len(df)), "label_noise": LABEL_NOISE,
                 "split": "time-based 70/15/15 on created_at", "train": int(len(train)),
                 "validation": int(len(val)), "test": int(len(test)),
                 "test_class_counts": {CLASSES[i]: int((y_te == i).sum()) for i in range(3)}},
        "test": {
            "accuracy": round(float(accuracy_score(y_te, pred_te)), 4),
            "macro_f1": round(float(f1_score(y_te, pred_te, average="macro")), 4),
            "weighted_f1": round(float(f1_score(y_te, pred_te, average="weighted")), 4),
            "per_class": class_metrics(y_te, p_te),
            "confusion_matrix": {"labels": CLASSES, "rows_true_cols_pred": confusion_matrix(y_te, pred_te, labels=[0, 1, 2]).tolist()},
            "brier_score_multiclass": round(multiclass_brier(p_te, y_te), 4),
            "reliability_table": reliability_table(p_te, y_te),
        },
        "cv_5fold_train": {
            "accuracy_mean": round(float(cv["test_accuracy"].mean()), 4),
            "accuracy_std": round(float(cv["test_accuracy"].std()), 4),
            "macro_f1_mean": round(float(cv["test_f1_macro"].mean()), 4),
            "macro_f1_std": round(float(cv["test_f1_macro"].std()), 4),
            "note": "stratified, shuffled folds within the training period (not time-ordered)",
        },
        "policy_on_test": {
            "review_at": review_at, "block_at": block_at,
            "high_blocked": round(float((d_te[y_te == 2] == "BLOCKED").mean()), 4),
            "high_approved": round(float((d_te[y_te == 2] == "APPROVED").mean()), 4),
            "low_approved": round(float((d_te[y_te == 0] == "APPROVED").mean()), 4),
            "manual_review_share": round(float((d_te == "HOLD").mean()), 4),
        },
        "feature_importances": {n: round(float(v), 4) for n, v in zip(FEATURE_NAMES, model.feature_importances_)},
    }

    if write:
        os.makedirs(EVAL_DIR, exist_ok=True)
        for name, part in (("train", train), ("validation", val), ("test", test)):
            part.to_csv(os.path.join(EVAL_DIR, f"{name}.csv"), index=False)
        sweep_df.to_csv(os.path.join(EVAL_DIR, "threshold_results.csv"), index=False)
        with open(os.path.join(EVAL_DIR, "false_negatives.jsonl"), "w", encoding="utf-8") as f:
            for i in np.where((y_te >= 1) & (d_te == "APPROVED"))[0]:
                row = test.iloc[int(i)]
                f.write(json.dumps({
                    "created_at": row["created_at"], "true_label": CLASSES[int(y_te[i])],
                    "predicted": CLASSES[int(pred_te[i])], "score": float(scores_te[i]),
                    "probabilities": [round(float(x), 4) for x in p_te[i]],
                    "features": {n: (float(row[n]) if isinstance(row[n], float) else int(row[n])) for n in FEATURE_NAMES},
                }) + "\n")
        trained_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        model_path = os.path.join(MODEL_DIR, "random_forest_model.pkl")
        joblib.dump({"model": model, "feature_names": FEATURE_NAMES, "classes": CLASSES, "random_state": SEED,
                     "sklearn_version": sklearn.__version__}, model_path, compress=3)
        card = {"sha256": sha256_file(model_path), "sklearn_version": sklearn.__version__,
                "feature_names": FEATURE_NAMES, "classes": CLASSES, "trained_at": trained_at,
                "generator": "synthetic_rule_v2", "random_state": SEED}
        with open(os.path.join(MODEL_DIR, "model_card.json"), "w", encoding="utf-8") as f:
            json.dump(card, f, indent=2)
        with open(os.path.join(MODEL_DIR, "metrics.json"), "w", encoding="utf-8") as f:
            json.dump({**metrics, "trained_at": trained_at}, f, indent=2)
        with open(os.path.join(EVAL_DIR, "final_evaluation_report.json"), "w", encoding="utf-8") as f:
            json.dump({"metrics": metrics, "model_card": card,
                       "files": ["train.csv", "validation.csv", "test.csv", "threshold_results.csv",
                                 "false_negatives.jsonl"]}, f, indent=2)
        old = os.path.join(MODEL_DIR, "dataset.csv")
        if os.path.exists(old):
            os.remove(old)
    return metrics


if __name__ == "__main__":
    m = train_and_evaluate()
    t = m["test"]
    print(f"test accuracy {t['accuracy']:.4f}  macro F1 {t['macro_f1']:.4f}  Brier {t['brier_score_multiclass']:.4f}")
    for c in CLASSES:
        pc = t["per_class"][c]
        print(f"  {c:6s} P {pc['precision']:.3f} R {pc['recall']:.3f} F1 {pc['f1']:.3f} PR-AUC {pc['pr_auc']:.3f} n={pc['support']}")
    cv = m["cv_5fold_train"]
    print(f"5-fold CV accuracy {cv['accuracy_mean']:.4f} ± {cv['accuracy_std']:.4f}; macro F1 {cv['macro_f1_mean']:.4f} ± {cv['macro_f1_std']:.4f}")
    print("policy on test:", m["policy_on_test"])
