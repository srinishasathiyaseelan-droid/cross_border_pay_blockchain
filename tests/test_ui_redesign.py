"""UI redesign ("Signed Ledger") regression checks: assets, page shell, one signature button per page, UI kit.

Spec: DESIGN.md, design-work/04-tokens.md, 05-components.md, 06-motion.md.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"

ADMIN_PAGES = ["/", "/dashboard", "/transactions", "/blockchain", "/admin/kyc",
               "/admin/ai", "/admin/reports", "/ui-kit"]
SME_PAGES = ["/", "/dashboard", "/payment", "/kyc", "/transactions", "/blockchain"]
PUBLIC_PAGES = ["/login", "/register", "/ui-kit"]


def _html(resp):
    assert resp.status_code == 200, resp.status_code
    return resp.get_data(as_text=True)


def _check_shell(html, path=""):
    # New layered CSS + motion layer, old monolithic stylesheet gone.
    for asset in ("css/tokens.css", "css/components.css", "css/pages.css",
                  "vendor/animejs/anime.umd.min.js", "js/motion.js"):
        assert asset in html, asset
    assert "css/style.css" not in html
    # Accessibility shell.
    assert 'class="skip-link" href="#main"' in html
    assert 'id="main"' in html
    # Offline: no CDN or web-font hosts.
    assert not re.search(r"https://(cdn|unpkg|fonts\.googleapis|fonts\.gstatic)", html)
    # The signature (hero) button appears at most once per page.
    # (The UI kit shows the light and dark themes side by side, so it has one per theme.)
    assert html.count("btn-hero") <= (2 if path == "/ui-kit" else 1)


@pytest.mark.parametrize("path", ADMIN_PAGES)
def test_admin_pages_use_new_shell(admin_client, path):
    _check_shell(_html(admin_client.get(path)), path)


@pytest.mark.parametrize("path", SME_PAGES)
def test_sme_pages_use_new_shell(sme_client, path):
    _check_shell(_html(sme_client.get(path)), path)


@pytest.mark.parametrize("path", PUBLIC_PAGES)
def test_public_pages_use_new_shell(client, path):
    _check_shell(_html(client.get(path)), path)


def test_current_nav_link_is_marked(admin_client):
    html = _html(admin_client.get("/dashboard"))
    current = re.findall(r'<a href="([^"]+)" class="nav-link" aria-current="page"', html)
    # Desktop bar + mobile sheet render the same list.
    assert current and set(current) == {"/dashboard"}


def test_ui_kit_shows_both_themes_and_core_components(client):
    html = _html(client.get("/ui-kit"))
    assert 'data-kit-theme="light"' in html and 'data-kit-theme="dark"' in html
    for cls in ("btn-primary", "btn-destructive", "is-busy", "toast", "pipeline", "receipt", "segmented",
                "advisory", "skeleton"):
        assert cls in html, cls


def test_anime_is_vendored_with_licence():
    assert (STATIC / "vendor/animejs/anime.umd.min.js").stat().st_size > 10_000
    assert "MIT" in (STATIC / "vendor/animejs/LICENSE.md").read_text(encoding="utf-8")
    assert "anime" in (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8").lower()
    assert not (STATIC / "css/style.css").exists()


def test_reduced_motion_zeroes_motion_tokens():
    css = (STATIC / "css/tokens.css").read_text(encoding="utf-8")
    block = css.split("@media (prefers-reduced-motion: reduce)", 1)[1].split("}", 2)[0]
    for token in ("--dur-instant: 0ms", "--dur-fast: 0ms", "--dur-base: 0ms", "--dur-slow: 0ms",
                  "--dur-page: 0ms", "--press-depth: 0px"):
        assert token in block, token
    js = (STATIC / "js/motion.js").read_text(encoding="utf-8")
    assert "prefers-reduced-motion: reduce" in js


def test_ai_output_is_only_inserted_as_text():
    # AI text must never be parsed as HTML in the browser (G-guardrails; DESIGN.md "AI is labelled and inert").
    js = (STATIC / "js/script.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js or not re.search(r"innerHTML\s*=\s*[^;]*(summary|explanation|answer|draft)", js)
