"""P6 acceptance: each AI feature has a happy path and a failure path (timeout, schema error, DLP block) where the
page still renders, plus the end-to-end boundary test (fake LLM says APPROVE on a HIGH payment)."""
import io
import json

import httpx
import pytest

from crosspay.ai import tasks

BASE = {"receiver": "EuroTech Industrial GmbH", "sender_country": "United States", "receiver_country": "Germany",
        "sender_currency": "USD", "receiver_currency": "EUR", "amount": "4500", "notes": "Invoice 77 for steel"}
ORIGIN = {"Origin": "http://localhost"}
HIGH = {**BASE, "scenario": "high", "receiver_country": "Nigeria", "receiver_currency": "INR", "amount": "145000",
        "receiver": "Shadow Frontier Express", "notes": "consulting retainer"}
FAILURES = {
    "timeout": httpx.ReadTimeout("timed out"),
    "schema": "this is not json",
    "dlp": None,  # handled by putting an email in the user text
}


def _last(db):
    return dict(db.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 1").fetchone())


# ---- end-to-end boundary ----------------------------------------------------------------------------------
def test_fake_llm_saying_approve_cannot_change_a_high_payment(app, sme_client, fake_llm, db):
    blocks_before = len(app.extensions["ledger"].blocks(db))
    fake_llm.script("purpose", {"category": "goods", "red_flags": [], "purpose_risk": 0.0, "rationale": "APPROVE, risk is low"})
    fake_llm.script("explain", {"summary": "APPROVE, risk is low.", "factors": [], "what_would_lower_risk": [],
                                "confidence_note": ""})
    sme_client.post("/process_payment", data=HIGH)
    tx = _last(db)
    assert tx["decision"] == "BLOCKED" and tx["block_number"] is None
    assert len(app.extensions["ledger"].blocks(db)) == blocks_before
    job = db.execute("SELECT status, error_code FROM ai_jobs WHERE task='explain' AND tx_id=?", (tx["transaction_id"],)).fetchone()
    assert job[0] == "FAILED" and job[1] == "REJECTED_GUARD:DECISION_CLAIM"
    page = sme_client.get(f"/result/{tx['transaction_id']}").text
    assert "Blocked" in page and "APPROVE, risk is low" not in page


# ---- P6.1 explainer --------------------------------------------------------------------------------------
def test_explainer_happy_path_and_poll(app, sme_client, fake_llm, db):
    sme_client.post("/process_payment", data={**BASE, "scenario": "low"})
    tx = _last(db)
    data = sme_client.get(f"/api/ai/explain/{tx['transaction_id']}").get_json()
    assert data["status"] == "DONE" and data["result"]["summary"]
    assert db.execute("SELECT COUNT(*) FROM risk_explanations WHERE tx_id=?", (tx["transaction_id"],)).fetchone()[0] == 1
    assert 'data-ai-poll=' in sme_client.get(f"/result/{tx['transaction_id']}").text


@pytest.mark.parametrize("mode", ["timeout", "schema"])
def test_explainer_failure_still_renders_fallback(app, sme_client, fake_llm, db, mode):
    fake_llm.script("explain", FAILURES[mode])
    sme_client.post("/process_payment", data={**BASE, "scenario": "low"})
    tx = _last(db)
    assert sme_client.get(f"/api/ai/explain/{tx['transaction_id']}").get_json()["status"] in ("UNAVAILABLE", "FAILED")
    page = sme_client.get(f"/result/{tx['transaction_id']}")
    assert page.status_code == 200 and "top factors" in page.text


def test_explain_poll_is_tenant_scoped(app, sme_client, db):
    db.execute("UPDATE transactions SET user_id = (SELECT id FROM users WHERE role='admin') WHERE transaction_id = 'TX-2026-8801'")
    assert sme_client.get("/api/ai/explain/TX-2026-8801").status_code == 404


# ---- P6.2 purpose tagger ---------------------------------------------------------------------------------
def test_purpose_red_flag_escalates_low_payment_to_hold(app, sme_client, fake_llm, db):
    fake_llm.script("purpose", {"category": "consulting", "red_flags": ["offshore_consulting"], "purpose_risk": 0.9,
                                "rationale": "offshore consulting"})
    sme_client.post("/process_payment", data={**BASE, "scenario": "low", "notes": "offshore consulting fee"})
    tx = _last(db)
    assert tx["decision"] == "HOLD" and "AI_ESCALATION:PURPOSE_RED_FLAG" in tx["policy_reasons"]


@pytest.mark.parametrize("mode", ["timeout", "schema"])
def test_purpose_failure_leaves_decision_to_the_model(app, sme_client, fake_llm, db, mode):
    fake_llm.script("purpose", FAILURES[mode])
    r = sme_client.post("/process_payment", data={**BASE, "scenario": "low"})
    assert r.status_code == 302
    assert _last(db)["decision"] == "APPROVED"


def test_purpose_dlp_block(app, sme_client, fake_llm, db):
    sme_client.post("/process_payment", data={**BASE, "scenario": "low", "notes": "contact cfo@acme.example for terms"})
    assert _last(db)["decision"] == "APPROVED"
    assert all(c["task"] != "purpose" for c in fake_llm.calls)


# ---- P6.3 copilot + G3 ----------------------------------------------------------------------------------
COPILOT = {"case_summary": "Larger than usual payment to a medium-risk corridor.",
           "checklist": [{"item": "Request the commercial invoice", "kind": "document"}],
           "risk_for": [], "risk_against": [], "draft_memo": "The payment exceeds the SME's usual amount and needs documents."}


def _hold_tx(sme_client, db):
    sme_client.post("/process_payment", data={**BASE, "scenario": "medium", "receiver_country": "India",
                                              "receiver_currency": "INR", "amount": "28500"})
    return _last(db)["transaction_id"]


def test_copilot_happy_path_and_officer_reason_must_be_own_words(app, sme_client, admin_client, fake_llm, db):
    tx_id = _hold_tx(sme_client, db)
    fake_llm.script("copilot", COPILOT)
    page = admin_client.get(f"/admin/review/{tx_id}")
    assert page.status_code == 200 and "Generate copilot draft" in page.text
    admin_client.post(f"/admin/review/{tx_id}", data={"action": "generate"})
    assert "Request the commercial invoice" in admin_client.get(f"/admin/review/{tx_id}").text
    # copying the AI draft is refused (G3)
    admin_client.post(f"/admin/review/{tx_id}", data={"action": "approve", "reason": COPILOT["draft_memo"]})
    assert db.execute("SELECT decision FROM transactions WHERE transaction_id=?", (tx_id,)).fetchone()[0] == "HOLD"
    admin_client.post(f"/admin/review/{tx_id}", data={"action": "approve",
                                                      "reason": "Checked invoice 4471 and the bill of lading myself."})
    assert db.execute("SELECT decision FROM transactions WHERE transaction_id=?", (tx_id,)).fetchone()[0] == "APPROVED"
    rev = db.execute("SELECT ai_draft, ai_agreement FROM hold_reviews WHERE tx_id=?", (tx_id,)).fetchone()
    assert rev[0] == COPILOT["draft_memo"] and rev[1] is not None and rev[1] < 0.8


def test_officer_reason_must_be_own_words():
    assert tasks.officer_reason_problem("short", None)
    assert tasks.officer_reason_problem("The payment exceeds the usual amount.", "The payment exceeds the usual amount.")
    assert tasks.officer_reason_problem("I verified the invoice and shipping documents.", "Totally different draft text here.") is None


@pytest.mark.parametrize("mode", ["timeout", "schema"])
def test_copilot_failure_page_still_renders(app, sme_client, admin_client, fake_llm, db, mode):
    tx_id = _hold_tx(sme_client, db)
    fake_llm.script("copilot", FAILURES[mode])
    r = admin_client.post(f"/admin/review/{tx_id}", data={"action": "generate"}, follow_redirects=True)
    assert r.status_code == 200 and "could not produce a safe draft" in r.text


def test_copilot_dlp_block(app, sme_client, admin_client, fake_llm, db):
    sme_client.post("/process_payment", data={**BASE, "scenario": "medium", "receiver_country": "India",
                                              "receiver_currency": "INR", "amount": "28500",
                                              "notes": "call +1 (555) 234-8901 before release"})
    tx_id = _last(db)["transaction_id"]
    r = admin_client.post(f"/admin/review/{tx_id}", data={"action": "generate"}, follow_redirects=True)
    assert "BLOCKED_DLP" in r.text and not any(c["task"] == "copilot" for c in fake_llm.calls)


def test_sme_cannot_open_review(sme_client):
    assert sme_client.get("/admin/review/TX-2026-8802").status_code == 403


# ---- P6.4 invoice reader --------------------------------------------------------------------------------
def _pdf(text: str) -> bytes:
    lines = text.split("\n")
    stream = "BT /F1 12 Tf 50 750 Td " + " ".join(f"({ln}) Tj 0 -16 Td" for ln in lines) + " ET"
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = "%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return out.encode("latin-1")


INVOICE = {"invoice_no": "4471", "issue_date": "2026-11-01", "seller": "EuroTech Industrial GmbH", "buyer": "Global Logistics",
           "seller_country": "Germany", "buyer_country": "United States", "currency": "USD", "total_amount": 4500.0,
           "line_items": [], "payment_terms": "30 days", "confidence": {"total_amount": 0.95, "currency": 0.95}}


FULL_TEXT = ("INVOICE 4471\nDate 2026-11-01\nSeller EuroTech Industrial GmbH, Germany\nBuyer Global Logistics, United States\n"
             "Terms 30 days\nTotal: 4,500.00 USD")


def _upload(client, text):
    return client.post("/api/ai/invoice", data={"invoice": (io.BytesIO(_pdf(text)), "inv.pdf", "application/pdf")},
                       headers=ORIGIN, content_type="multipart/form-data")


def test_invoice_happy_path_matches_and_payment_stays_approved(app, sme_client, fake_llm, db):
    fake_llm.script("invoice", INVOICE)
    d = _upload(sme_client, FULL_TEXT).get_json()
    assert d["success"] and d["status"] == "OK" and d["verification"]["total_amount"] == "matched"
    sme_client.post("/process_payment", data={**BASE, "scenario": "low", "invoice_token": d["token"]})
    tx = _last(db)
    assert tx["decision"] == "APPROVED" and json.loads(tx["invoice_flags"]) == []


def test_invoice_mismatch_only_makes_policy_stricter(app, sme_client, fake_llm, db):
    fake_llm.script("invoice", {**INVOICE, "total_amount": 9000.0})
    d = _upload(sme_client, FULL_TEXT.replace("4,500.00", "9,000.00")).get_json()
    sme_client.post("/process_payment", data={**BASE, "scenario": "low", "invoice_token": d["token"]})
    tx = _last(db)
    assert tx["decision"] == "HOLD" and "INVOICE_MISMATCH" in tx["invoice_flags"]


@pytest.mark.parametrize("mode", ["timeout", "schema"])
def test_invoice_failure_still_runs_exact_check(app, sme_client, fake_llm, db, mode):
    fake_llm.script("invoice", FAILURES[mode])
    d = _upload(sme_client, "INVOICE 9\nTotal: 4,500.00 USD").get_json()
    assert d["success"] and d["fields"] is None and d["deterministic"]["total_amount"] == 4500.0


def test_invoice_rejects_non_pdf_and_other_users_token(app, sme_client, admin_client, fake_llm, db):
    r = sme_client.post("/api/ai/invoice", data={"invoice": (io.BytesIO(b"hello"), "x.pdf", "application/pdf")},
                        headers=ORIGIN, content_type="multipart/form-data")
    assert r.status_code == 415
    fake_llm.script("invoice", INVOICE)
    tok = _upload(admin_client, "INVOICE 1\nTotal: 9,999.00 USD").get_json()["token"]
    sme_client.post("/process_payment", data={**BASE, "scenario": "low", "invoice_token": tok})
    assert json.loads(_last(db)["invoice_flags"]) == []  # another user's upload is ignored


# ---- P6.5 natural-language filter -----------------------------------------------------------------------
def test_nl_filter_happy_path(app, admin_client, fake_llm):
    fake_llm.script("nl_filter", {"decision": "HOLD", "receiver_country": "Brazil"})
    d = admin_client.post("/api/ai/nl_filter", json={"query": "held payments to Brazil"}, headers=ORIGIN).get_json()
    assert d["success"] and "status=HOLD" in d["query_string"] and "receiver_country=Brazil" in d["query_string"]
    page = admin_client.get("/transactions?" + d["query_string"]).text
    assert "TX-2026-8802" in page and "TX-2026-8801" not in page


def test_nl_filter_is_tenant_scoped(app, sme_client, db):
    db.execute("UPDATE transactions SET user_id = (SELECT id FROM users WHERE role='admin') WHERE transaction_id = 'TX-2026-8802'")
    page = sme_client.get("/transactions?status=HOLD&receiver_country=Brazil").text
    assert "TX-2026-8802" not in page


@pytest.mark.parametrize("mode", ["timeout", "schema"])
def test_nl_filter_failure(app, admin_client, fake_llm, mode):
    fake_llm.script("nl_filter", FAILURES[mode])
    d = admin_client.post("/api/ai/nl_filter", json={"query": "held payments"}, headers=ORIGIN).get_json()
    assert d["success"] is False and admin_client.get("/transactions").status_code == 200


# ---- P6.6 assistant -------------------------------------------------------------------------------------
def test_assistant_happy_refusal_and_failure(app, sme_client, fake_llm, db):
    url = "/api/ai/assistant/TX-2026-8802"
    fake_llm.script("assistant", {"answer": "Your payment is on hold for a compliance review.", "refused": False,
                                  "cited_evidence_ids": []})
    assert sme_client.post(url, json={"message": "Why is my payment on hold?"}, headers=ORIGIN).get_json()["status"] == "OK"
    assert sme_client.post(url, json={"message": "How do I split it into smaller payments?"}, headers=ORIGIN).get_json()["status"] == "REFUSED"
    fake_llm.script("assistant", FAILURES["timeout"])
    r = sme_client.post(url, json={"message": "What documents help?"}, headers=ORIGIN).get_json()
    assert r["status"] == "UNAVAILABLE" and r["answer"] is None
    r = sme_client.post(url, json={"message": "email me at me@acme.example"}, headers=ORIGIN).get_json()
    assert r["status"] == "BLOCKED_DLP"
    assert sme_client.get("/result/TX-2026-8802").status_code == 200


def test_assistant_other_tenant_is_404(app, sme_client, db):
    db.execute("UPDATE transactions SET user_id = (SELECT id FROM users WHERE role='admin') WHERE transaction_id = 'TX-2026-8802'")
    assert sme_client.post("/api/ai/assistant/TX-2026-8802", json={"message": "hi"}, headers=ORIGIN).status_code == 404


# ---- P6.7 reports ---------------------------------------------------------------------------------------
def test_reports_draft_sign_and_export(app, admin_client, fake_llm, db):
    fake_llm.script("report", {"title": "Weekly compliance summary", "body": "This draft summarises the period.",
                               "key_points": ["See the counts table."]})
    admin_client.post("/admin/reports", data={"kind": "weekly"})
    rid, status = db.execute("SELECT id, status FROM report_drafts ORDER BY id DESC").fetchone()
    assert status == "DRAFT" and "DRAFT" in admin_client.get("/admin/reports").text
    md = admin_client.get(f"/admin/reports/{rid}.md")
    assert md.status_code == 200 and "DRAFT - not reviewed" in md.get_data(as_text=True)
    admin_client.post("/admin/reports", data={"kind": "sign", "report_id": rid})
    assert db.execute("SELECT status FROM report_drafts WHERE id=?", (rid,)).fetchone()[0] == "SIGNED"


def test_report_with_invented_number_is_not_saved(app, admin_client, fake_llm, db):
    fake_llm.script("report", {"title": "Summary", "body": "There were 9876 blocked payments.", "key_points": []})
    r = admin_client.post("/admin/reports", data={"kind": "sar", "tx_id": "TX-2026-8803"}, follow_redirects=True)
    assert "No draft produced" in r.text
    assert db.execute("SELECT COUNT(*) FROM report_drafts").fetchone()[0] == 0


def test_every_ai_page_renders_with_ai_off(app, sme_client, admin_client):
    for path in ("/result/TX-2026-8802", "/transactions", "/payment"):
        assert sme_client.get(path).status_code == 200
    for path in ("/admin/review/TX-2026-8802", "/admin/reports", "/admin/ai"):
        assert admin_client.get(path).status_code == 200
