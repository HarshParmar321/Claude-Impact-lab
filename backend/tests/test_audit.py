import pandas as pd

from app.calculations import audit as A
from app.services.data_store import get_store


def wo(**kw):
    base = dict(work_order_id="W1", complaint_id="C1", road_id="R1", work_type="pothole_patch", repair_method="hot_mix",
                rate_card_id="RC02", area_sqm=10.0, cost_inr=26000, completed_date="2025-08-01")
    base.update(kw)
    return base


RC = pd.DataFrame([dict(rate_card_id="RC02", unit="per sqm", standard_rate_inr=2600),
                   dict(rate_card_id="RC09", unit="per job", standard_rate_inr=14500)])


def test_expected_cost_per_sqm_and_per_job():
    df = pd.DataFrame([wo(), wo(work_order_id="W2", rate_card_id="RC09", area_sqm=0, cost_inr=29000)])
    r = A.compute_rate_checks(df, RC).set_index("work_order_id")
    assert r.loc["W1", "expected_cost_inr"] == 26000 and r.loc["W1", "rate_ratio"] == 1.0
    assert r.loc["W2", "expected_cost_inr"] == 14500 and r.loc["W2", "rate_ratio"] == 2.0


def test_rate_bands_match_spec_thresholds():
    assert A.rate_band(0.74, 1) == "LOW_OUTLIER"
    assert A.rate_band(0.75, 1) == "NORMAL"
    assert A.rate_band(1.30, 1) == "NORMAL"
    assert A.rate_band(1.35, 1) == "CONTEXT"
    assert A.rate_band(1.40, 1) == "CONTEXT"
    assert A.rate_band(1.41, 1) == "REVIEW"
    assert A.rate_band(None, 0) == "NOT_BILLED"


def test_duplicate_rule_requires_all_conditions():
    a = wo()
    b = wo(work_order_id="W2", complaint_id="", cost_inr=26500, completed_date="2025-08-03")
    assert list(A.detect_duplicates(pd.DataFrame([a, b])).flagged_id) == ["W2"]
    # 5 days apart -> no
    assert A.detect_duplicates(pd.DataFrame([a, dict(b, completed_date="2025-08-06")])).empty
    # cost 10% apart -> no
    assert A.detect_duplicates(pd.DataFrame([a, dict(b, cost_inr=28600)])).empty
    # both have complaints -> no
    assert A.detect_duplicates(pd.DataFrame([a, dict(b, complaint_id="C2")])).empty
    # different method -> no
    assert A.detect_duplicates(pd.DataFrame([a, dict(b, repair_method="cold_mix")])).empty


def test_golden_case_rules_and_dedup_count():
    s = get_store()
    row = s.audit_idx.loc["WO25-02469"]
    assert row.rules == ["DLP_REVIEW", "POSSIBLE_DUPLICATE"]
    assert row.lead_count == 1
    assert row.duplicate_partner_id == "WO25-01483"
    assert row.expected_cost_inr == 15640  # 3.4 sqm × ₹4,600


def test_multi_rule_orders_count_once():
    s = get_store()
    summ = A.lead_summary(s.audit)
    leads = s.audit[s.audit.is_review_lead]
    assert summ["unique_review_leads"] == leads.work_order_id.nunique() == len(leads)
    primary_hits = sum(summ["rule_hits"][r] for r in A.PRIMARY_RULES)
    assert summ["leads_with_multiple_rules"] > 0
    assert primary_hits > summ["unique_review_leads"]  # summing rules would overcount


def test_data_quality_outliers_are_not_overbilling_leads():
    s = get_store()
    dq = s.audit[s.audit.is_data_quality_flag]
    assert len(dq) > 0
    assert not dq.is_review_lead.any()
    assert (dq.rate_ratio < 0.75).all()


def test_context_band_not_a_lead_by_itself():
    s = get_store()
    ctx = s.audit[(s.audit.rate_band == "CONTEXT") & (s.audit.rules.map(len) == 0)]
    assert len(ctx) > 0 and not ctx.is_review_lead.any()
