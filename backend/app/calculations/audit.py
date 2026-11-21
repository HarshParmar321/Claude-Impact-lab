"""Deterministic audit rules (spec §7). Claude never calculates any of this.

If an existing, validated calculation module is available (e.g. Kshitij's
pandas modules), wire it in through ``app/services/audit_adapter.py`` and keep
these functions as the reference implementation used by the tests.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# --- Rate-card thresholds (spec §7.2). Do not change silently. -------------
LOW_COST_BELOW = 0.75
NORMAL_MAX = 1.30
CONTEXT_MAX = 1.40

RATE_BANDS = {
    "LOW_OUTLIER": f"Below {LOW_COST_BELOW:.2f}×: low-cost/data-quality outlier (not overbilling)",
    "NORMAL": f"{LOW_COST_BELOW:.2f}×–{NORMAL_MAX:.2f}×: normal range",
    "CONTEXT": f"Above {NORMAL_MAX:.2f}×–{CONTEXT_MAX:.2f}×: context band (shown, not a primary anomaly)",
    "REVIEW": f"Above {CONTEXT_MAX:.2f}×: rate-card review lead",
    "NOT_BILLED": "₹0 to BMC (executed under warranty); no rate check",
}

# --- Duplicate-like rule parameters (spec §7.3) ----------------------------
DUP_MAX_DAYS = 4
DUP_MAX_COST_DIFF_PCT = 6.0
DUP_MAX_AREA_DIFF_PCT = 5.0

PRIMARY_RULES = ("DLP_REVIEW", "POSSIBLE_DUPLICATE", "RATE_CARD_REVIEW")

EVIDENCE_TEXT = {
    "photos": "Geotagged before/after photographs",
    "mb": "Measurement book entry",
    "cert": "Engineer completion certificate",
    "separate": "Separate-defect justification: why the second record represents separate work",
    "emergency": "Emergency-work approval (if emergency rates were applied)",
    "deviation": "Itemised rate deviation approval",
    "dlp_contract": "Original DLP contract and identity of the warranty holder (Ward Warranty Desk)",
    "dlp_scope": "Confirmation whether the defect falls within DLP scope",
}


def rate_band(ratio: float | None, cost: float) -> str:
    if cost <= 0 or ratio is None or np.isnan(ratio):
        return "NOT_BILLED"
    if ratio < LOW_COST_BELOW:
        return "LOW_OUTLIER"
    if ratio <= NORMAL_MAX:
        return "NORMAL"
    if ratio <= CONTEXT_MAX:
        return "CONTEXT"
    return "REVIEW"


def compute_rate_checks(work_orders: pd.DataFrame, rate_card: pd.DataFrame) -> pd.DataFrame:
    """Expected cost and rate ratio per work order (spec §7.1)."""
    rc = rate_card.set_index("rate_card_id")
    df = work_orders[["work_order_id", "rate_card_id", "area_sqm", "cost_inr"]].copy()
    unit = df.rate_card_id.map(rc["unit"])
    rate = df.rate_card_id.map(rc["standard_rate_inr"]).astype(float)
    df["unit"] = unit
    df["standard_rate_inr"] = rate
    df["expected_cost_inr"] = np.where(unit == "per sqm", df.area_sqm.astype(float) * rate, rate).round(0)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = df.cost_inr.astype(float) / df.expected_cost_inr
    df["rate_ratio"] = np.where(df.cost_inr > 0, ratio, np.nan).round(3)
    df["rate_band"] = [rate_band(r, c) for r, c in zip(df.rate_ratio, df.cost_inr)]
    return df[["work_order_id", "unit", "standard_rate_inr", "expected_cost_inr", "rate_ratio", "rate_band"]]


@dataclass
class DuplicatePair:
    flagged_id: str
    partner_id: str
    days_apart: int
    area_diff_pct: float
    cost_diff_pct: float


def detect_duplicates(work_orders: pd.DataFrame) -> pd.DataFrame:
    """Duplicate-like work orders (spec §7.3).

    A record is flagged when it has no linked complaint and another paid order
    exists on the same road with the same work type and repair method, the same
    or nearly the same area, completed within 4 days, and cost within 6%.
    When both lack a complaint, the later record is flagged.
    """
    wo = work_orders[work_orders.cost_inr > 0].copy()
    wo["completed"] = pd.to_datetime(wo.completed_date)
    pairs: list[dict] = []
    for _, g in wo.groupby(["road_id", "work_type", "repair_method"], sort=False):
        if len(g) < 2:
            continue
        g = g.sort_values(["completed", "work_order_id"])
        recs = g.to_dict("records")
        for i in range(len(recs)):
            for j in range(i + 1, len(recs)):
                a, b = recs[i], recs[j]
                days = abs((b["completed"] - a["completed"]).days)
                if days > DUP_MAX_DAYS:
                    break
                a_missing = not a["complaint_id"]
                b_missing = not b["complaint_id"]
                if not (a_missing or b_missing):
                    continue
                flagged, partner = (b, a) if b_missing else (a, b)
                amax = max(float(a["area_sqm"]), float(b["area_sqm"]))
                area_diff = 0.0 if amax == 0 else abs(float(a["area_sqm"]) - float(b["area_sqm"])) / amax * 100
                if area_diff > DUP_MAX_AREA_DIFF_PCT:
                    continue
                cost_diff = abs(float(flagged["cost_inr"]) - float(partner["cost_inr"])) / float(partner["cost_inr"]) * 100
                if cost_diff > DUP_MAX_COST_DIFF_PCT:
                    continue
                pairs.append(dict(flagged_id=flagged["work_order_id"], partner_id=partner["work_order_id"],
                                  days_apart=int(days), area_diff_pct=round(area_diff, 2), cost_diff_pct=round(cost_diff, 2)))
    cols = ["flagged_id", "partner_id", "days_apart", "area_diff_pct", "cost_diff_pct"]
    df = pd.DataFrame(pairs, columns=cols)
    # one row per flagged record: keep the closest partner
    return df.sort_values(["flagged_id", "days_apart", "cost_diff_pct"]).drop_duplicates("flagged_id").reset_index(drop=True)


def dlp_flags(work_orders: pd.DataFrame, roads: pd.DataFrame) -> pd.Series:
    """dlp_review = road.under_dlp == 'Y' and work_order.cost_inr > 0 (spec §7.4)."""
    under = work_orders.road_id.map(roads.set_index("road_id").under_dlp)
    return (under == "Y") & (work_orders.cost_inr > 0)


def initial_verdict(rules: list[str]) -> str:
    """Verdict precedence (spec §9)."""
    if "DLP_REVIEW" in rules:
        return "WARRANTY_REVIEW"
    if "POSSIBLE_DUPLICATE" in rules or "RATE_CARD_REVIEW" in rules:
        return "HOLD_FOR_EVIDENCE"
    return "RELEASE_PAYMENT"


def lead_confidence(rules: list[str], ratio: float | None, dup: dict | None) -> str:
    """How strongly the records support the review lead (not a judgement of intent)."""
    if "DLP_REVIEW" in rules:
        return "HIGH"  # DLP status and payment are recorded facts
    if dup is not None and dup["days_apart"] <= 2 and dup["cost_diff_pct"] <= 3 and dup["area_diff_pct"] <= 1:
        return "HIGH"
    if "RATE_CARD_REVIEW" in rules and ratio is not None and ratio >= 1.75:
        return "HIGH"
    if rules and rules != ["LOW_COST_DATA_QUALITY"]:
        return "MEDIUM"
    return "LOW"


def evidence_required(rules: list[str], wo: dict) -> list[str]:
    items: list[str] = []
    if "DLP_REVIEW" in rules:
        items += [EVIDENCE_TEXT["dlp_contract"], EVIDENCE_TEXT["dlp_scope"]]
    if "POSSIBLE_DUPLICATE" in rules:
        items += [EVIDENCE_TEXT["photos"], EVIDENCE_TEXT["mb"], EVIDENCE_TEXT["separate"]]
    if "RATE_CARD_REVIEW" in rules:
        items += [EVIDENCE_TEXT["deviation"], EVIDENCE_TEXT["mb"], EVIDENCE_TEXT["emergency"]]
    if "LOW_COST_DATA_QUALITY" in rules:
        items += [EVIDENCE_TEXT["mb"]]
    if rules:
        if wo.get("photo_before") != "Y" or wo.get("photo_after") != "Y":
            items.append(EVIDENCE_TEXT["photos"])
        if wo.get("measurement_book") != "Y":
            items.append(EVIDENCE_TEXT["mb"])
        if wo.get("engineer_certificate") != "Y":
            items.append(EVIDENCE_TEXT["cert"])
    seen, out = set(), []
    for i in items:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def evidence_completeness(wo: dict) -> dict:
    fields = {"photo_before": "Before photo", "photo_after": "After photo",
              "measurement_book": "Measurement book", "engineer_certificate": "Completion certificate"}
    present = [label for f, label in fields.items() if wo.get(f) == "Y"]
    missing = [label for f, label in fields.items() if wo.get(f) != "Y"]
    return {"score_pct": round(100 * len(present) / len(fields)), "present": present, "missing": missing}


def build_audit_table(work_orders: pd.DataFrame, roads: pd.DataFrame, rate_card: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (audit table with one row per work order, duplicate pairs).

    ``is_review_lead`` is True when any PRIMARY rule fires. A work order caught
    by several rules is still ONE lead (spec §7.5): ``lead_count`` is always 1
    for leads and 0 otherwise.
    """
    rates = compute_rate_checks(work_orders, rate_card)
    dups = detect_duplicates(work_orders)
    dup_map = dups.set_index("flagged_id").to_dict("index")
    df = work_orders.merge(rates, on="work_order_id", how="left")
    df["dlp_review"] = dlp_flags(df, roads)
    rules_col, verdicts, conf, evid, partners = [], [], [], [], []
    for rec in df.to_dict("records"):
        rules = []
        if rec["dlp_review"]:
            rules.append("DLP_REVIEW")
        if rec["work_order_id"] in dup_map:
            rules.append("POSSIBLE_DUPLICATE")
        if rec["rate_band"] == "REVIEW":
            rules.append("RATE_CARD_REVIEW")
        if rec["rate_band"] == "LOW_OUTLIER":
            rules.append("LOW_COST_DATA_QUALITY")
        dup = dup_map.get(rec["work_order_id"])
        rules_col.append(rules)
        verdicts.append(initial_verdict(rules))
        ratio = None if pd.isna(rec["rate_ratio"]) else float(rec["rate_ratio"])
        conf.append(lead_confidence(rules, ratio, dup))
        evid.append(evidence_required(rules, rec))
        partners.append(dup["partner_id"] if dup else "")
    df["rules"] = rules_col
    df["recommended_verdict"] = verdicts
    df["confidence"] = conf
    df["evidence_required"] = evid
    df["duplicate_partner_id"] = partners
    df["is_review_lead"] = df.rules.map(lambda r: any(x in PRIMARY_RULES for x in r))
    df["is_data_quality_flag"] = df.rules.map(lambda r: r == ["LOW_COST_DATA_QUALITY"])
    df["lead_count"] = df.is_review_lead.astype(int)
    return df, dups


def lead_summary(audit: pd.DataFrame) -> dict:
    """Deduplicated counts. Rule counts are reported separately and never summed."""
    leads = audit[audit.is_review_lead]
    rule_counts = {r: int(audit.rules.map(lambda x, r=r: r in x).sum()) for r in
                   ("DLP_REVIEW", "POSSIBLE_DUPLICATE", "RATE_CARD_REVIEW", "LOW_COST_DATA_QUALITY")}
    multi = int(leads.rules.map(lambda x: sum(1 for r in x if r in PRIMARY_RULES) > 1).sum())
    return {
        "unique_review_leads": int(len(leads)),
        "amount_requiring_review_inr": int(leads.cost_inr.sum()),
        "rule_hits": rule_counts,
        "leads_with_multiple_rules": multi,
        "data_quality_flags": int(audit.is_data_quality_flag.sum()),
        "context_band_orders": int((audit.rate_band == "CONTEXT").sum()),
    }
