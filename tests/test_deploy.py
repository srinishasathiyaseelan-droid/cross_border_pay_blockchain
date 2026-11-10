"""Deployment readiness: health probe and render.yaml sanity."""
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_healthz_is_public_and_ok(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_render_blueprint_has_no_secret_values():
    with open(os.path.join(ROOT, "render.yaml"), encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    svc = spec["services"][0]
    assert svc["healthCheckPath"] == "/healthz"
    # One worker: the live feed bus, job queue and rate limiter are in-process.
    assert "--workers 1" in svc["startCommand"]
    secret_like = ("KEY", "TOKEN", "SECRET", "PASSWORD", "ACCOUNT_ID")
    for var in svc["envVars"]:
        if any(s in var["key"] for s in secret_like) and not var["key"].startswith("LLM_"):
            assert "value" not in var, f"{var['key']} must be set in the Render dashboard, not in render.yaml"
