"""Deterministic Fair Hearing assembled from the audit rules.

Used when there is no API key, the API call fails, or Claude's JSON fails
validation, and no cached response exists for the evidence hash.
"""

from __future__ import annotations


def _inr(v) -> str:
    return f"₹{int(v):,}"


def build_template_hearing(ev: dict) -> dict:
    wo = ev["work_order"]
    rules = ev["rules_triggered"]
    rate = ev["rate_check"]
    dup = ev.get("duplicate_comparison")
    dlp = ev["dlp"]
    ctx = ev["context"]
    wid = wo["work_order_id"]

    a_evidence, a_src = [], {wid}
    if "DLP_REVIEW" in rules:
        a_evidence.append(f"{wo['road_id']} is under DLP until {dlp['dlp_end_date']}, yet BMC was billed {_inr(wo['cost_inr'])} for {wid}.")
        a_src.add(wo["road_id"])
    if dup:
        other = dup["partner_id"] if dup["flagged_id"] == wid else dup["flagged_id"]
        a_evidence.append(
            f"{dup['flagged_id']} (no linked complaint) matches {dup['partner_id']} on road, work type and repair method, "
            f"{dup['days_apart']} day(s) apart, area difference {dup['area_diff_pct']}%, cost difference {dup['cost_diff_pct']}%.")
        a_src.update([dup["flagged_id"], dup["partner_id"], other])
    if rate["rate_ratio"] is not None:
        a_evidence.append(
            f"Billed {_inr(rate['actual_cost_inr'])} against an expected {_inr(rate['expected_cost_inr'])} "
            f"({rate['rate_ratio']}×; band: {rate['rate_band']}, review threshold above 1.40×).")
        a_src.add(rate["rate_card_id"])
    for c in ev["record_conflicts"]:
        a_evidence.append(c["text"])
        a_src.update(c["source_ids"])
    missing = [k for k in ("photo_before", "photo_after", "measurement_book", "engineer_certificate") if wo.get(k) != "Y"]
    if missing:
        a_evidence.append(f"{wid} is missing: {', '.join(m.replace('_', ' ') for m in missing)}.")

    ctx_items, f_src = [], set()
    if dup:
        ctx_items.append("A second defect on the same road can legitimately need a separate patch of similar size; "
                         "the records cannot show whether the two orders cover different locations.")
    heavy = [r for r in ctx["rainfall"] if r["rainfall_mm"] >= 60]
    if heavy:
        days = ", ".join(f"{r['date']} ({r['rainfall_mm']} mm)" for r in heavy[:3])
        ctx_items.append(f"Heavy rainfall in the ward around the repair ({days}) can cause early failure of fresh patches.")
    if ctx["flood_hotspots"]:
        h = ctx["flood_hotspots"][0]
        ctx_items.append(f"Flood hotspot {h['hotspot_id']} lies {h['distance_m']} m from the road; standing water accelerates surface damage.")
        f_src.add(h["hotspot_id"])
    if "RATE_CARD_REVIEW" in rules:
        ctx_items.append("Emergency or night work, small-quantity premiums or an approved rate deviation can raise unit cost above the standard rate.")
    if "DLP_REVIEW" in rules:
        ctx_items.append("The original DLP contractor may have been unavailable or the defect may fall outside DLP scope; "
                         "the contractor on this work order is not shown to be the warranty holder.")
    if "LOW_COST_DATA_QUALITY" in rules:
        ctx_items.append("A low billed amount may reflect a measurement-entry error rather than under-delivery.")
    t = ctx["traffic"]
    ctx_items.append(f"The road carries {t['peak_hour_vehicles']:,} peak-hour vehicles (congestion {t['congestion_index']}/10), "
                     "so heavy wear between repairs is plausible.")
    if not ctx_items:
        ctx_items.append("No additional legitimate context was found in the supplied records.")

    verdict = ev["rule_based_verdict"]
    if verdict == "WARRANTY_REVIEW":
        reasoning = ("Verdict precedence places DLP review first. Liability for this repair cannot be settled until the Ward "
                     "Warranty Desk identifies the original DLP owner; other open questions are captured in the evidence request.")
        citizen = ("This road is still under a repair guarantee (Defect Liability Period). Before BMC pays, the ward's warranty desk "
                   "will check who is responsible for fixing it. This is a review, not a finding against anyone.")
    elif verdict == "HOLD_FOR_EVIDENCE":
        reasoning = "An audit rule remains unresolved by the records. Payment should wait for the listed documents, which can clear the lead."
        citizen = "Payment for this repair is on hold until supporting documents are checked. This is a routine review, not a finding of wrongdoing."
    else:
        reasoning = "No material audit rule remains unresolved."
        citizen = "This repair has no open review issues, so the standard payment process continues."

    officer = (f"{wid} · {wo['road_name']} · {_inr(wo['cost_inr'])}. Rules: {', '.join(rules) or 'none'}. "
               f"Recommend {verdict.replace('_', ' ').title()}. Request: {'; '.join(ev['rule_based_evidence_required'][:4]) or 'none'}.")

    return {
        "auditor_case": {
            "summary": f"{wid} triggered {len([r for r in rules if r != 'LOW_COST_DATA_QUALITY'])} review rule(s): "
                       f"{', '.join(rules) if rules else 'none'}. This is a review lead, not proof of intent.",
            "evidence": a_evidence or ["No audit rule evidence."],
            "source_ids": sorted(s for s in a_src if s in ev["source_ids"]),
        },
        "fairness_case": {
            "possible_legitimate_context": ctx_items,
            "limitations": ev["data_limitations"],
            "source_ids": sorted(s for s in (f_src | {wid}) if s in ev["source_ids"]),
        },
        "recommended_verdict": verdict,
        "reasoning": reasoning,
        "evidence_required": ev["rule_based_evidence_required"],
        "citizen_explanation": citizen,
        "officer_brief": officer,
        "confidence": ev["lead_confidence"],
    }
