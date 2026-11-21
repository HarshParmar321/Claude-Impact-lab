import json

from app.calculations.audit import initial_verdict
from app.calculations import budget
from app.schemas import contains_forbidden
from app.services.data_store import get_store
from app.services.hearing_service import build_evidence, validate_output
from app.templates.hearing_fallback import build_template_hearing


def test_verdict_precedence():
    assert initial_verdict(["DLP_REVIEW", "POSSIBLE_DUPLICATE", "RATE_CARD_REVIEW"]) == "WARRANTY_REVIEW"
    assert initial_verdict(["POSSIBLE_DUPLICATE"]) == "HOLD_FOR_EVIDENCE"
    assert initial_verdict(["RATE_CARD_REVIEW"]) == "HOLD_FOR_EVIDENCE"
    assert initial_verdict(["LOW_COST_DATA_QUALITY"]) == "RELEASE_PAYMENT"
    assert initial_verdict([]) == "RELEASE_PAYMENT"


def test_every_lead_has_one_of_three_verdicts():
    a = get_store().audit
    assert set(a[a.is_review_lead].recommended_verdict) <= {"RELEASE_PAYMENT", "HOLD_FOR_EVIDENCE", "WARRANTY_REVIEW"}
    assert (a[a.rules.map(lambda r: "DLP_REVIEW" in r)].recommended_verdict == "WARRANTY_REVIEW").all()


def test_template_hearing_is_valid_and_neutral_for_every_lead_type():
    from sqlmodel import Session
    from app.database import engine, init_db
    from app.services import audit_adapter
    init_db()
    s = get_store()
    samples = ["WO25-02469", "WO25-02270"] + s.audit[s.audit.rules.map(lambda r: r == ["RATE_CARD_REVIEW"])].work_order_id.head(2).tolist()
    with Session(engine) as session:
        for wo in samples:
            ev = build_evidence(audit_adapter.build_case(s, session, wo))
            out, problems = validate_output(build_template_hearing(ev), ev)
            assert out is not None, problems
            assert not contains_forbidden(json.dumps(out))
            assert out["recommended_verdict"] == ev["rule_based_verdict"]


def test_validator_rejects_invented_ids_and_forbidden_words():
    from sqlmodel import Session
    from app.database import engine, init_db
    from app.services import audit_adapter
    init_db()
    s = get_store()
    with Session(engine) as session:
        ev = build_evidence(audit_adapter.build_case(s, session, "WO25-02469"))
    good = build_template_hearing(ev)
    bad_ids = json.loads(json.dumps(good)); bad_ids["auditor_case"]["source_ids"].append("WO99-99999")
    assert validate_output(bad_ids, ev)[0] is None
    bad_word = json.loads(json.dumps(good)); bad_word["reasoning"] = "This is fraud."
    assert validate_output(bad_word, ev)[0] is None
    bad_schema = json.loads(json.dumps(good)); bad_schema["recommended_verdict"] = "BLOCK"
    assert validate_output(bad_schema, ev)[0] is None


def test_planner_never_exceeds_budget():
    s = get_store()
    for ward in s.wards.ward_code:
        for b in (0, 15_000, 100_000, 1_000_000):
            p = budget.plan(ward, b, 0, s.priority, s.durability)
            assert p["allocated_inr"] <= b
            assert p["remaining_inr"] == b - p["allocated_inr"]
            assert all(w["new_bmc_allocation_inr"] == 0 and not w["counted_as_saving"] for w in p["warranty_routes"])
