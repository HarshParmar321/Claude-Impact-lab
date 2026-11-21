import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["data_loaded"] and h["claude_mode"] in ("cache", "template")


def test_summary_counts_are_deduplicated(client):
    s = client.get("/api/summary").json()
    c = s["cards"]
    assert c["unique_review_leads"] < sum(c["rule_hits"][r] for r in ("DLP_REVIEW", "POSSIBLE_DUPLICATE", "RATE_CARD_REVIEW"))
    assert s["sankey"]["nodes"] and s["sankey"]["links"]


def test_review_filters(client):
    r = client.get("/api/reviews", params={"ward": "M/E", "rule": "POSSIBLE_DUPLICATE"}).json()
    ids = [i["work_order_id"] for i in r["items"]]
    assert "WO25-02469" in ids
    assert all(i["ward_code"] == "M/E" and "POSSIBLE_DUPLICATE" in i["rules"] for i in r["items"])


def test_golden_case_end_to_end(client):
    case = client.get("/api/reviews/WO25-02469").json()
    assert case["recommended_verdict"] == "WARRANTY_REVIEW"
    assert case["duplicate"]["partner_id"] == "WO25-01483"
    assert case["dlp"]["warranty_owner_known"] is False
    langs = {c["language"] for c in case["complaints"]}
    assert {"en", "mr"} <= langs
    types = {c["type"] for c in case["record_conflicts"]}
    assert {"CATEGORY_TEXT_CONFLICT", "LATER_ROAD_CONDITION_SIGNAL", "NO_LINKED_COMPLAINT"} <= types
    signal = [c for c in case["record_conflicts"] if c["type"] == "LATER_ROAD_CONDITION_SIGNAL"][0]
    assert "does not prove causation" in signal["text"]

    h = client.post("/api/reviews/WO25-02469/hearing").json()
    assert h["mode"] == "cache"
    assert h["recommended_verdict"] == "WARRANTY_REVIEW"
    assert set(h["auditor_case"]["source_ids"]) <= set(h["supplied_source_ids"])

    t = client.post("/api/reviews/WO25-02469/hearing", params={"force_template": True}).json()
    assert t["mode"] == "template"


def test_override_requires_reason(client):
    r = client.patch("/api/reviews/WO25-02270/verdict", json={"verdict": "RELEASE_PAYMENT", "officer_reason": ""})
    assert r.status_code == 422
    r = client.patch("/api/reviews/WO25-02270/verdict", json={"verdict": "RELEASE_PAYMENT", "officer_reason": "Photos show two separate potholes 40 m apart."})
    assert r.status_code == 200 and r.json()["decision"]["is_override"] is True


def test_receipt_and_failed_feedback_creates_warranty_case(client):
    for lang in ("en", "mr", "hi", "hinglish"):
        r = client.get("/api/receipts/WO25-01483", params={"language": lang}).json()
        assert r["language"] == lang and r["dlp"]["under_dlp"]
    fb = client.post("/api/receipts/WO25-01483/durability-feedback",
                     json={"answer": "FAILED", "description": "Pothole is back", "language": "en"}).json()
    assert fb["case_type"] == "WARRANTY_REVIEW"
    assert fb["feedback"]["generated_warranty_review"] is True
    assert "Ward Warranty Desk" in fb["feedback"]["routed_to"]
    ok = client.post("/api/receipts/WO25-01483/durability-feedback", json={"answer": "SURVIVED", "language": "hi"}).json()
    assert ok["case_type"] is None


def test_scorecards_state_peer_group_and_sample(client):
    cs = client.get("/api/scorecards/contractors").json()["items"]
    for c in cs:
        assert c["sample_size"] > 0
        for g in c["peer_groups"]:
            assert g["peer_group"] and g["sample_size"] > 0 and g["peer_sample_size"] >= g["sample_size"]
    w = client.get("/api/scorecards/wards/M/E").json()
    assert set(w["attribution"]) == {"contractor_delivery", "ward_system", "data_quality"}


def test_planner_budget_cap(client):
    p = client.get("/api/planner/recommendations", params={"ward_code": "M/E", "budget_inr": 100000}).json()
    assert p["allocated_inr"] <= 100000
    assert any(w["road_id"] == "RD0235" for w in p["warranty_routes"])
