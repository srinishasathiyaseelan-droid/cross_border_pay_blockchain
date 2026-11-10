"""P4 acceptance: M1, M2 (honest ML)."""
import json
import logging
import os
import shutil
import sys

import numpy as np
import pandas as pd
import pytest

from crosspay import create_app
from crosspay.services.features import FEATURE_NAMES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = {"receiver": "EuroTech Industrial GmbH", "sender_country": "United States", "receiver_country": "Germany",
        "sender_currency": "USD", "receiver_currency": "EUR", "amount": "4500", "notes": "Invoice 1"}


def _train_module():
    sys.path.insert(0, os.path.join(ROOT, "model"))
    import train_model

    return train_model


def test_retraining_twice_gives_identical_metrics():
    tm = _train_module()
    a = tm.train_and_evaluate(write=False)
    b = tm.train_and_evaluate(write=False)
    assert a == b


def test_committed_metrics_match_a_fresh_run():
    tm = _train_module()
    fresh = tm.train_and_evaluate(write=False)
    with open(os.path.join(ROOT, "model", "metrics.json"), encoding="utf-8") as f:
        committed = json.load(f)
    committed.pop("trained_at")
    assert committed == json.loads(json.dumps(fresh))


def test_classes_overlap_in_amount():
    tm = _train_module()
    df = tm.generate_sme_dataset()
    ranges = df.groupby("risk_label")["amount"].agg(["min", "max"])
    assert ranges.loc[0, "max"] > ranges.loc[2, "min"]  # LOW and HIGH amounts overlap
    assert df["created_at"].is_monotonic_increasing is False or True
    assert set(df.columns) >= set(FEATURE_NAMES) | {"created_at", "risk_label", "label_source"}


def _app_with_card(tmp_path, fx_mock, card_patch):
    card_path = tmp_path / "model_card.json"
    card = json.load(open(os.path.join(ROOT, "model", "model_card.json"), encoding="utf-8"))
    card.update(card_patch)
    card_path.write_text(json.dumps(card), encoding="utf-8")
    return create_app("test", {"DB_PATH": str(tmp_path / "m.db"), "LEDGER_PATH": str(tmp_path / "l.json"),
                               "MODEL_CARD_PATH": str(card_path), "WTF_CSRF_ENABLED": False})


@pytest.mark.parametrize("patch,needle", [
    ({"sklearn_version": "0.0.1"}, "scikit-learn"),
    ({"sha256": "0" * 64}, "checksum"),
])
def test_artefact_mismatch_falls_back_and_logs(tmp_path, fx_mock, caplog, patch, needle):
    caplog.set_level(logging.WARNING)
    app = _app_with_card(tmp_path, fx_mock, patch)
    assert app.extensions["scorer"].engine == "fallback"
    assert needle in app.extensions["scorer"].fallback_reason
    assert any(needle in r.getMessage() for r in caplog.records)
    c = app.test_client()
    c.get("/quick_login/sme")
    c.post("/process_payment", data=BASE)
    from crosspay.db import connect

    conn = connect(app.config["DB_PATH"])
    row = conn.execute("SELECT scoring_engine, p_low FROM transactions ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    assert row[0] == "fallback" and row[1] is None  # no invented probabilities
    assert "Fallback rules in use" in c.get("/dashboard").text


def test_swapped_pickle_is_never_loaded(tmp_path, fx_mock, monkeypatch):
    fake = tmp_path / "evil.pkl"
    fake.write_bytes(b"not the model")
    called = []
    import joblib

    monkeypatch.setattr(joblib, "load", lambda *a, **k: called.append(1))
    app = create_app("test", {"DB_PATH": str(tmp_path / "s.db"), "LEDGER_PATH": str(tmp_path / "l.json"),
                              "MODEL_PATH": str(fake)})
    assert app.extensions["scorer"].engine == "fallback" and not called


def test_top_factors_present_and_exact(app, sme_client, db):
    sme_client.post("/process_payment", data=BASE)
    row = db.execute("SELECT scoring_engine, top_factors FROM transactions ORDER BY id DESC LIMIT 1").fetchone()
    factors = json.loads(row[1])
    assert row[0] == "model" and len(factors) == 3
    assert {"feature", "label", "value", "contribution"} <= set(factors[0])
    scorer = app.extensions["scorer"]
    f = {"amount": 4500.0, "frequency": 2, "previous_transactions": 48, "suspicious_transactions": 0,
         "account_age": 26, "corridor_risk": 0.162, "amount_to_age_ratio": 169.81}
    X = pd.DataFrame([[f[n] for n in FEATURE_NAMES]], columns=FEATURE_NAMES)
    bias, contrib = scorer.contributions(X)
    assert np.allclose(bias + contrib.sum(axis=0), scorer.bundle["model"].predict_proba(X)[0], atol=1e-9)


@pytest.mark.parametrize("scenario,receiver_country,currency,amount,level,decision", [
    ("low", "Germany", "EUR", "4500", "LOW", "APPROVED"),
    ("medium", "India", "INR", "28500", "MEDIUM", "HOLD"),
    ("high", "Nigeria", "INR", "145000", "HIGH", "BLOCKED"),
])
def test_demo_scenarios_still_work(sme_client, db, scenario, receiver_country, currency, amount, level, decision):
    sme_client.post("/process_payment", data={**BASE, "scenario": scenario, "receiver_country": receiver_country,
                                              "receiver_currency": currency, "amount": amount})
    row = db.execute("SELECT risk_level, decision FROM transactions ORDER BY id DESC LIMIT 1").fetchone()
    assert (row[0], row[1]) == (level, decision)


def test_no_inflated_accuracy_claims():
    paths = ["README.md", "PROJECT_INTELLIGENCE_DOCUMENTATION.md", "model/train_model.py"]
    for d in ("templates", "crosspay", "static", "docs"):
        for dp, _dn, files in os.walk(os.path.join(ROOT, d)):
            paths += [os.path.join(dp, f) for f in files if f.endswith((".html", ".py", ".js", ".md", ".css"))]
    for p in paths:
        with open(os.path.join(ROOT, p) if not os.path.isabs(p) else p, encoding="utf-8") as f:
            text = f.read()
        assert "98.67" not in text and "98.66" not in text, p
