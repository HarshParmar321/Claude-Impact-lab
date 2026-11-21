"""Wraps the deterministic audit calculations for the API.

Swap ``app.calculations.audit`` for an existing validated module here if one
exists; the API layer only depends on the functions in this file.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
from sqlmodel import Session, select

from app.calculations import audit as audit_calc
from app.calculations.scorecards import text_category
from app.models import DurabilityFeedback, OfficerDecision
from app.services.data_store import DataStore

THRESHOLDS = [
    {"band": "LOW_OUTLIER", "label": "Below 0.75×", "meaning": "Low-cost/data-quality outlier; not overbilling"},
    {"band": "NORMAL", "label": "0.75×–1.30×", "meaning": "Normal range"},
    {"band": "CONTEXT", "label": "Above 1.30×–1.40×", "meaning": "Context band; shown but not a primary anomaly"},
    {"band": "REVIEW", "label": "Above 1.40×", "meaning": "Rate-card review lead"},
]

WT_TO_CAT = {"pothole_patch": "pothole", "surface_restoration": "road_surface",
             "trench_reinstatement": "road_surface", "drain_cover_replacement": "drain_cover"}

WARRANTY_SUBTITLE = "Route to Ward Warranty Desk to identify the original DLP owner and verify whether BMC should pay."


def _clean(v):
    if isinstance(v, float) and pd.isna(v):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


def latest_decisions(session: Session) -> dict[str, OfficerDecision]:
    rows = session.exec(select(OfficerDecision).order_by(OfficerDecision.created_at)).all()
    return {r.work_order_id: r for r in rows}


def lead_dict(rec: dict, decision: OfficerDecision | None = None) -> dict:
    return {
        "work_order_id": rec["work_order_id"],
        "ward_code": rec["ward_code"],
        "road_id": rec["road_id"],
        "road_name": rec["road_name"],
        "contractor_id": rec["contractor_id"],
        "contractor_name": rec["contractor_name"],
        "repair_method": rec["repair_method"],
        "work_type": rec["work_type"],
        "completed_date": rec["completed_date"],
        "amount_inr": int(rec["cost_inr"]),
        "expected_amount_inr": int(rec["expected_cost_inr"]),
        "rate_ratio": _clean(rec["rate_ratio"]),
        "rate_band": rec["rate_band"],
        "rules": list(rec["rules"]),
        "recommended_verdict": rec["recommended_verdict"],
        "confidence": rec["confidence"],
        "is_review_lead": bool(rec["is_review_lead"]),
        "lead_count": int(rec["lead_count"]),
        "duplicate_partner_id": rec["duplicate_partner_id"] or None,
        "has_linked_complaint": bool(rec["complaint_id"]),
        "final_verdict": decision.final_verdict if decision else None,
        "decision_status": "DECIDED" if decision else "AWAITING_OFFICER",
    }


def list_leads(store: DataStore, session: Session, *, ward=None, contractor=None, rule=None, verdict=None,
               repair_method=None, include_data_quality=False, q=None, limit=50, offset=0) -> dict:
    df = store.audit
    mask = df.is_review_lead | (df.is_data_quality_flag if include_data_quality else False)
    df = df[mask]
    if ward:
        df = df[df.ward_code == ward]
    if contractor:
        df = df[df.contractor_id == contractor]
    if repair_method:
        df = df[df.repair_method == repair_method]
    if rule:
        df = df[df.rules.map(lambda r: rule in r)]
    decisions = latest_decisions(session)
    if verdict:
        cur = df.apply(lambda r: decisions[r.work_order_id].final_verdict if r.work_order_id in decisions else r.recommended_verdict, axis=1) if len(df) else pd.Series(dtype=str)
        df = df[cur == verdict] if len(df) else df
    if q:
        ql = q.lower()
        df = df[df.work_order_id.str.lower().str.contains(ql) | df.road_name.str.lower().str.contains(ql)]
    # golden/high-confidence first, then amount
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    df = df.assign(_c=df.confidence.map(order), _m=df.rules.map(len)).sort_values(["_c", "_m", "cost_inr"], ascending=[True, False, False])
    total = len(df)
    page = df.iloc[offset: offset + limit]
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "amount_requiring_review_inr": int(df[df.is_review_lead].cost_inr.sum()),
        "items": [lead_dict(r, decisions.get(r["work_order_id"])) for r in page.to_dict("records")],
        "filters": {
            "wards": sorted(store.audit.ward_code.unique().tolist()),
            "contractors": store.contractors[["contractor_id", "contractor_name"]].to_dict("records"),
            "repair_methods": sorted(store.audit.repair_method.unique().tolist()),
            "rules": ["RATE_CARD_REVIEW", "POSSIBLE_DUPLICATE", "DLP_REVIEW", "LOW_COST_DATA_QUALITY"],
            "verdicts": ["RELEASE_PAYMENT", "HOLD_FOR_EVIDENCE", "WARRANTY_REVIEW"],
        },
    }


# ---------------------------------------------------------------------------
# Case detail
# ---------------------------------------------------------------------------

def _wo_facts(rec: dict) -> dict:
    keys = ["work_order_id", "complaint_id", "road_id", "road_name", "ward_code", "contractor_id", "contractor_name",
            "work_type", "repair_method", "rate_card_id", "area_sqm", "cost_inr", "billed_to", "payment_status",
            "issued_date", "completed_date", "recorded_date", "sla_tier", "sla_days", "sla_met", "reopened_within_30d",
            "photo_before", "photo_after", "measurement_book", "engineer_certificate"]
    return {k: _clean(rec[k]) for k in keys}


def _complaint_dict(c: dict) -> dict:
    keys = ["complaint_id", "created_at", "channel", "language", "text_original", "text_en", "category", "upvotes",
            "status", "duplicate_of", "linked_work_order_id", "closed_at", "road_id", "ward_code"]
    out = {k: _clean(c[k]) for k in keys}
    out["text_suggests_category"] = text_category(c["text_en"])
    return out


def build_case(store: DataStore, session: Session, wo_id: str) -> dict | None:
    rec = store.work_order(wo_id)
    if rec is None:
        return None
    road = store.road(rec["road_id"])
    completed = date.fromisoformat(rec["completed_date"])
    issued = date.fromisoformat(rec["issued_date"])
    sources: set[str] = {wo_id, rec["road_id"], rec["rate_card_id"], rec["contractor_id"]}

    # --- complaints ---------------------------------------------------------
    comp = store.complaints
    linked = comp[comp.complaint_id == rec["complaint_id"]] if rec["complaint_id"] else comp.iloc[0:0]
    dup_of_linked = comp[comp.duplicate_of.isin(linked.complaint_id)] if len(linked) else comp.iloc[0:0]
    window_start = datetime.combine(issued - timedelta(days=14), datetime.min.time())
    window_end = datetime.combine(completed + timedelta(days=30), datetime.max.time())
    same_issue = WT_TO_CAT.get(rec["work_type"], "pothole")
    on_road = comp[(comp.road_id == rec["road_id"]) & (comp.category == same_issue)].copy()
    on_road["_t"] = pd.to_datetime(on_road.created_at)
    on_road = on_road[(on_road._t >= window_start) & (on_road._t <= window_end)]
    complaint_ids = list(dict.fromkeys(list(linked.complaint_id) + list(dup_of_linked.complaint_id) + list(on_road.complaint_id)))
    complaints = [_complaint_dict(store.complaint(c)) for c in complaint_ids]
    sources.update(complaint_ids)

    # --- rate check ---------------------------------------------------------
    rate = dict(
        rate_card_id=rec["rate_card_id"], unit=rec["unit"], standard_rate_inr=int(rec["standard_rate_inr"]),
        area_sqm=_clean(rec["area_sqm"]), expected_cost_inr=int(rec["expected_cost_inr"]), actual_cost_inr=int(rec["cost_inr"]),
        rate_ratio=_clean(rec["rate_ratio"]), rate_band=rec["rate_band"], band_meaning=audit_calc.RATE_BANDS[rec["rate_band"]],
        thresholds=THRESHOLDS,
        formula=("expected = area_sqm × standard_rate" if rec["unit"] == "per sqm" else "expected = standard_rate (per job)") + "; ratio = actual ÷ expected",
    )

    # --- duplicate comparison ---------------------------------------------
    dup = None
    d = store.duplicates
    hit = d[(d.flagged_id == wo_id) | (d.partner_id == wo_id)]
    if len(hit):
        h = hit.iloc[0].to_dict()
        a = store.work_order(h["partner_id"])
        b = store.work_order(h["flagged_id"])
        dup = dict(
            role="FLAGGED_RECORD" if h["flagged_id"] == wo_id else "EARLIER_RECORD",
            flagged_id=h["flagged_id"], partner_id=h["partner_id"], days_apart=int(h["days_apart"]),
            area_diff_pct=float(h["area_diff_pct"]), cost_diff_pct=float(h["cost_diff_pct"]),
            criteria=[
                {"label": "Flagged record has no linked complaint", "met": not b["complaint_id"]},
                {"label": "Same road", "met": a["road_id"] == b["road_id"], "detail": a["road_id"]},
                {"label": "Same work type", "met": a["work_type"] == b["work_type"], "detail": a["work_type"]},
                {"label": "Same repair method", "met": a["repair_method"] == b["repair_method"], "detail": a["repair_method"]},
                {"label": f"Area within {audit_calc.DUP_MAX_AREA_DIFF_PCT:.0f}%", "met": True, "detail": f"{h['area_diff_pct']}% difference"},
                {"label": f"Completed ≤ {audit_calc.DUP_MAX_DAYS} days apart", "met": True, "detail": f"{int(h['days_apart'])} day(s)"},
                {"label": f"Cost within {audit_calc.DUP_MAX_COST_DIFF_PCT:.0f}%", "met": True, "detail": f"{h['cost_diff_pct']}% difference"},
            ],
            same_contractor=a["contractor_id"] == b["contractor_id"],
            side_by_side=[_wo_facts(a), _wo_facts(b)],
            label="Duplicate-like records (possible duplicate charge) — not a confirmed finding",
        )
        sources.update([h["flagged_id"], h["partner_id"]])
        if a["complaint_id"]:
            sources.add(a["complaint_id"])

    # --- DLP ---------------------------------------------------------------
    dlp = dict(
        under_dlp=road["under_dlp"] == "Y", dlp_start_date=road["dlp_start_date"] or None, dlp_end_date=road["dlp_end_date"] or None,
        paid_by_bmc=int(rec["cost_inr"]) > 0, warranty_owner_known=False,
        note=("Road is within its Defect Liability Period and BMC was billed for this repair. The dataset does not identify the "
              "original DLP contractor, so the current work-order contractor is NOT assumed to be the warranty holder. "
              "Liability is unresolved and sits with the Ward Warranty Desk as a ward/system control issue." if road["under_dlp"] == "Y" and int(rec["cost_inr"]) > 0
              else ("Road is under DLP and this job was executed under warranty at ₹0 to BMC." if road["under_dlp"] == "Y" else "Road is not under a Defect Liability Period.")),
        routing=WARRANTY_SUBTITLE if road["under_dlp"] == "Y" and int(rec["cost_inr"]) > 0 else None,
    )

    # --- road context -------------------------------------------------------
    t = store.traffic[store.traffic.road_id == rec["road_id"]].iloc[0].to_dict()
    acc = store.accidents[store.accidents.road_id == rec["road_id"]].copy()
    acc["_d"] = pd.to_datetime(acc.date).dt.date
    acc = acc[(acc._d >= issued - timedelta(days=30)) & (acc._d <= completed + timedelta(days=45))]
    accidents = []
    for a in acc.to_dict("records"):
        after = a["_d"] > completed
        accidents.append(dict(accident_id=a["accident_id"], date=a["date"], severity=a["severity"], vehicle_type=a["vehicle_type"],
                              road_condition_related=a["road_condition_related"] == "Y", reported_cause=a["reported_cause"],
                              after_completion=after))
        sources.add(a["accident_id"])
    hs = store.flood_hotspots[store.flood_hotspots.nearest_road_id == rec["road_id"]].to_dict("records")
    sources.update(h["hotspot_id"] for h in hs)
    rain = store.rainfall[(store.rainfall.ward_code == rec["ward_code"])].copy()
    rain["_d"] = pd.to_datetime(rain.date).dt.date
    rain = rain[(rain._d >= issued - timedelta(days=3)) & (rain._d <= completed + timedelta(days=14))]
    tides = store.tides.copy()
    tides["_d"] = pd.to_datetime(tides.date).dt.date
    tides = tides[(tides._d >= issued - timedelta(days=3)) & (tides._d <= completed + timedelta(days=14)) & (tides.high_tide_alert == "Y")]
    prio = store.priority[store.priority.road_id == rec["road_id"]].iloc[0]
    social = store.social_posts[(store.social_posts.road_id == rec["road_id"]) & (store.social_posts.linked_complaint_id != "")]
    social = social[social.linked_complaint_id.isin(complaint_ids) | (pd.to_datetime(social.posted_at).dt.date >= completed)]
    social_posts = [dict(post_id=s["post_id"], platform=s["platform"], posted_at=s["posted_at"], text=s["text"],
                         linked_complaint_id=s["linked_complaint_id"], link_basis=s["link_basis"]) for s in social.to_dict("records")
                    if pd.to_datetime(s["posted_at"]).date() <= completed + timedelta(days=30)]
    sources.update(s["post_id"] for s in social_posts)
    context = dict(
        road=dict(road_id=road["road_id"], road_name=road["road_name"], ward_code=road["ward_code"], road_class=road["road_class"],
                  best_bus_route=road["best_bus_route"] == "Y", bus_routes=int(road["bus_routes_count"]), low_lying=road["low_lying"] == "Y",
                  lat=road["centroid_lat"], lon=road["centroid_lon"]),
        traffic=dict(peak_hour_vehicles=int(t["peak_hour_vehicles"]), congestion_index=float(t["congestion_index"]),
                     bus_routes=int(t["bus_routes"]), two_wheeler_share=float(t["two_wheeler_share"]), survey_date=t["survey_date"]),
        accidents=accidents,
        flood_hotspots=[dict(hotspot_id=h["hotspot_id"], name=h["hotspot_name"], distance_m=int(h["distance_m"]), severity=h["severity"],
                             tide_sensitive=h["tide_sensitive"] == "Y") for h in hs],
        rainfall=[dict(date=r["date"], rainfall_mm=float(r["rainfall_mm"])) for r in rain.to_dict("records")],
        tide_alerts=[dict(date=x["date"], high_tide_m=float(x["high_tide_m"])) for x in tides.to_dict("records")],
        facilities_nearby=dict(hospitals=int(prio.hospitals_nearby), schools=int(prio.schools_nearby)),
        priority_score=float(prio.priority_score),
        social_posts=social_posts,
    )

    # --- record conflicts (deterministic) ---------------------------------
    conflicts = []
    if not rec["complaint_id"]:
        conflicts.append(dict(type="NO_LINKED_COMPLAINT", source_ids=[wo_id],
                              text=f"{wo_id} cites no citizen complaint, so the trail from complaint to payment is incomplete."))
    for c in complaints:
        sug = c["text_suggests_category"]
        if sug and sug != c["category"]:
            parent = c["duplicate_of"]
            extra = f" and was closed as a duplicate of {parent}" if parent else ""
            conflicts.append(dict(type="CATEGORY_TEXT_CONFLICT", source_ids=[c["complaint_id"]] + ([parent] if parent else []),
                                  text=f"{c['complaint_id']} ({c['language']}) describes a {sug.replace('_', ' ')} issue but is categorised as "
                                       f"'{c['category'].replace('_', ' ')}'{extra}. No {sug.replace('_', ' ')} work order is linked."))
        if c["status"] == "CLOSED_DUPLICATE" and c["duplicate_of"]:
            parent = store.complaint(c["duplicate_of"])
            if parent and parent["created_at"] > c["created_at"]:
                conflicts.append(dict(type="DUPLICATE_OF_LATER_COMPLAINT", source_ids=[c["complaint_id"], parent["complaint_id"]],
                                      text=f"{c['complaint_id']} was filed before {parent['complaint_id']} but closed as its duplicate."))
        created = datetime.fromisoformat(c["created_at"]).date()
        other_wo = c["linked_work_order_id"] and c["linked_work_order_id"] != wo_id
        if created > completed and (created - completed).days <= 30 and c["category"] == same_issue and not other_wo:
            conflicts.append(dict(type="LATER_COMPLAINT_AFTER_COMPLETION", source_ids=[c["complaint_id"], wo_id],
                                  text=f"{c['complaint_id']} ({created.isoformat()}, {(created - completed).days} days after completion) reports the problem on this road again, "
                                       f"while the work order records reopened_within_30d = {rec['reopened_within_30d']}."))
    later_acc = [a for a in accidents if a["after_completion"] and a["road_condition_related"]
                 and (date.fromisoformat(a["date"]) - completed).days <= 30]
    if later_acc:
        conflicts.append(dict(type="LATER_ROAD_CONDITION_SIGNAL", source_ids=[a["accident_id"] for a in later_acc] + [wo_id],
                              text="A later road-condition signal conflicts with the completion record and supports physical verification; "
                                   "it does not prove causation."))

    # --- timeline -----------------------------------------------------------
    timeline = []
    for c in complaints:
        timeline.append(dict(at=c["created_at"], kind="complaint", source_id=c["complaint_id"],
                             title=f"Complaint {c['complaint_id']} ({c['language']}, {c['upvotes']} upvotes)", detail=c["text_en"]))
        if c["status"] == "CLOSED_DUPLICATE":
            timeline.append(dict(at=c["closed_at"], kind="complaint_closed", source_id=c["complaint_id"],
                                 title=f"{c['complaint_id']} closed as duplicate of {c['duplicate_of']}", detail=f"Category recorded: {c['category']}"))
    wos_for_timeline = [_wo_facts(rec)] + ([x for x in dup["side_by_side"] if x["work_order_id"] != wo_id] if dup else [])
    for w in wos_for_timeline:
        timeline.append(dict(at=w["issued_date"], kind="work_order_issued", source_id=w["work_order_id"],
                             title=f"{w['work_order_id']} issued to {w['contractor_name']}",
                             detail=f"{w['work_type']} · {w['repair_method']} · {w['area_sqm']} sqm · complaint: {w['complaint_id'] or 'none'}"))
        timeline.append(dict(at=w["completed_date"], kind="work_order_completed", source_id=w["work_order_id"],
                             title=f"{w['work_order_id']} completed · ₹{int(w['cost_inr']):,} billed",
                             detail=f"SLA {w['sla_tier']} ({'met' if w['sla_met'] == 'Y' else 'missed'}); payment status {w['payment_status']}"))
    for a in accidents:
        if a["road_condition_related"]:
            timeline.append(dict(at=a["date"], kind="accident", source_id=a["accident_id"],
                                 title=f"Road-condition accident {a['accident_id']} ({a['severity']}, {a['vehicle_type']})",
                                 detail=f"Reported cause: {a['reported_cause']}. Correlation only; not causation."))
    for s in social_posts:
        timeline.append(dict(at=s["posted_at"], kind="social", source_id=s["post_id"], title=f"Public post {s['post_id']} ({s['platform']})",
                             detail=f"{s['text']} — linked because: {s['link_basis']}"))
    timeline.sort(key=lambda e: (e["at"][:10], e["at"]))

    decisions = session.exec(select(OfficerDecision).where(OfficerDecision.work_order_id == wo_id).order_by(OfficerDecision.created_at)).all()
    feedback = session.exec(select(DurabilityFeedback).where(DurabilityFeedback.work_order_id == wo_id).order_by(DurabilityFeedback.created_at)).all()
    latest = decisions[-1] if decisions else None

    data_limitations = [
        "The dataset does not identify the original DLP (warranty) contractor for any road.",
        "No photographs are attached to the dataset; photo fields are Y/N flags only and were not verified.",
        "Accident records are correlated by road ID and date only; they cannot establish causation.",
        "Complaint translations are provided in the dataset and were not independently verified.",
    ]

    return dict(
        lead=lead_dict(rec, latest),
        work_order=_wo_facts(rec),
        contractor=dict(contractor_id=rec["contractor_id"], contractor_name=rec["contractor_name"]),
        complaints=complaints,
        rate_check=rate,
        duplicate=dup,
        dlp=dlp,
        context=context,
        record_conflicts=conflicts,
        timeline=timeline,
        rules=list(rec["rules"]),
        recommended_verdict=rec["recommended_verdict"],
        verdict_precedence="DLP review → Warranty Review; else duplicate or rate anomaly → Hold for Evidence; else → Release Payment",
        warranty_subtitle=WARRANTY_SUBTITLE,
        evidence_required=list(rec["evidence_required"]),
        evidence_completeness=audit_calc.evidence_completeness(rec),
        confidence=rec["confidence"],
        data_limitations=data_limitations,
        decisions=[d.model_dump(mode="json") for d in decisions],
        durability_feedback=[f.model_dump(mode="json") for f in feedback],
        source_ids=sorted(sources),
    )


def record_decision(store: DataStore, session: Session, wo_id: str, verdict: str, reason: str) -> OfficerDecision:
    rec = store.work_order(wo_id)
    if rec is None:
        raise KeyError(wo_id)
    is_override = verdict != rec["recommended_verdict"]
    if not reason:
        raise ValueError("A written reason is required to save a decision" + (" (override)" if is_override else ""))
    if is_override and len(reason) < 10:
        raise ValueError("An override requires a short written reason (at least 10 characters)")
    d = OfficerDecision(work_order_id=wo_id, recommended_verdict=rec["recommended_verdict"], final_verdict=verdict,
                        is_override=is_override, officer_reason=reason)
    session.add(d)
    session.commit()
    session.refresh(d)
    return d


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

def overview(store: DataStore, session: Session, ward_cards: list[dict], contractor_cards: list[dict]) -> dict:
    a = store.audit
    s = audit_calc.lead_summary(a)
    decisions = latest_decisions(session)
    current = a.apply(lambda r: decisions[r.work_order_id].final_verdict if r.work_order_id in decisions else r.recommended_verdict, axis=1)

    comp = store.complaints
    linkage_rate = round(float((a.complaint_id != "").mean()) * 100, 1)

    # Sankey: complaints → issue → outcome → verdict
    cat_label = {"pothole": "Pothole", "drain_cover": "Drain cover", "waterlogging": "Waterlogging", "road_surface": "Road surface"}
    nodes = ["Citizen complaints"] + list(cat_label.values()) + ["Linked to work order", "Closed as duplicate", "No work order",
                                                                  "Work orders without complaint", "Release Payment", "Hold for Evidence", "Warranty Review"]
    idx = {n: i for i, n in enumerate(nodes)}
    links = []
    for cat, label in cat_label.items():
        cc = comp[comp.category == cat]
        if len(cc):
            links.append(dict(source=idx["Citizen complaints"], target=idx[label], value=int(len(cc))))
        for outcome, m in (("Linked to work order", cc.linked_work_order_id != ""), ("Closed as duplicate", cc.status == "CLOSED_DUPLICATE"),
                           ("No work order", (cc.linked_work_order_id == "") & (cc.status != "CLOSED_DUPLICATE"))):
            if int(m.sum()):
                links.append(dict(source=idx[label], target=idx[outcome], value=int(m.sum())))
    vmap = {"RELEASE_PAYMENT": "Release Payment", "HOLD_FOR_EVIDENCE": "Hold for Evidence", "WARRANTY_REVIEW": "Warranty Review"}
    for src, m in (("Linked to work order", a.complaint_id != ""), ("Work orders without complaint", a.complaint_id == "")):
        vc = current[m].value_counts()
        for v, n in vc.items():
            links.append(dict(source=idx[src], target=idx[vmap[v]], value=int(n)))

    leads = a[a.is_review_lead]
    by_road = leads.groupby("road_id").agg(n=("work_order_id", "size"), amount=("cost_inr", "sum"), ids=("work_order_id", list))
    roads = store.roads.set_index("road_id")
    lead_points = [dict(road_id=r, road_name=roads.loc[r, "road_name"], ward_code=roads.loc[r, "ward_code"], lat=float(roads.loc[r, "centroid_lat"]),
                        lon=float(roads.loc[r, "centroid_lon"]), leads=int(v.n), amount_inr=int(v.amount), work_order_ids=v.ids[:5])
                   for r, v in by_road.iterrows()]
    top = store.priority.sort_values("priority_score", ascending=False).head(25)
    priority_points = [dict(road_id=r.road_id, road_name=r.road_name, ward_code=r.ward_code, lat=float(r.centroid_lat), lon=float(r.centroid_lon),
                            priority_score=float(r.priority_score), under_dlp=r.under_dlp == "Y") for r in top.itertuples()]

    worst_wards = sorted(ward_cards, key=lambda w: w["overall_score"])[:4]
    ward_summary = [dict(ward_code=w["ward_code"], ward_name=w["ward_name"], overall_score=w["overall_score"],
                         main_system_issue=max(w["attribution"]["ward_system"].items(), key=lambda kv: kv[1] if "inr" not in kv[0] else -1)[0],
                         unique_review_leads=w["metrics"]["unique_review_leads"]) for w in worst_wards]
    below = [c for c in contractor_cards if (c["gap_vs_peers"]["durability"] or 0) < -3 or (c["gap_vs_peers"]["sla_reliability"] or 0) < -3]
    contractor_summary = dict(
        contractors=len(contractor_cards),
        below_peers_on_delivery=[dict(contractor_id=c["contractor_id"], contractor_name=c["contractor_name"],
                                      sla_gap=c["gap_vs_peers"]["sla_reliability"], durability_gap=c["gap_vs_peers"]["durability"],
                                      sample_size=c["sample_size"]) for c in below],
        dlp_leads_not_attributed=int(s["rule_hits"]["DLP_REVIEW"]),
    )
    return dict(
        cards=dict(
            unique_review_leads=s["unique_review_leads"],
            amount_requiring_review_inr=s["amount_requiring_review_inr"],
            linkage_rate_pct=linkage_rate,
            dlp_review_count=s["rule_hits"]["DLP_REVIEW"],
            rule_hits=s["rule_hits"],
            leads_with_multiple_rules=s["leads_with_multiple_rules"],
            data_quality_flags=s["data_quality_flags"],
            context_band_orders=s["context_band_orders"],
            work_orders=int(len(a)),
            complaints=int(len(comp)),
            decisions_recorded=len(decisions),
        ),
        ward_summary=ward_summary,
        contractor_summary=contractor_summary,
        sankey=dict(nodes=[{"name": n} for n in nodes], links=links),
        map=dict(lead_points=lead_points, priority_points=priority_points),
        methodology=[
            "Each work order counts once as a review lead, however many rules it triggers; rule hits are shown separately and never summed.",
            "Rate-card thresholds: <0.75× data-quality outlier · 0.75–1.30× normal · 1.30–1.40× context band (not counted) · >1.40× review lead.",
            "Duplicate-like: no linked complaint, same road/work type/method, area within 5%, ≤4 days apart, cost within 6%.",
            "DLP review: road under DLP and BMC billed > ₹0. Routed to the Ward Warranty Desk; not attributed to the current contractor.",
            "Amounts are 'requiring review', not confirmed loss. All data in this demo is synthetic.",
        ],
    )
