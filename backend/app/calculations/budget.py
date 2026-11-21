"""Recover, then reinvest: risk prioritisation and a budget-capped planner (spec §12)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

PRIORITY_WEIGHTS = {
    "accidents": 25,          # road-condition accidents, severity weighted
    "traffic": 15,            # peak-hour vehicles and congestion
    "bus_exposure": 10,       # BEST bus routes
    "flood": 10,              # proximity to a flood hotspot
    "rain_tide": 5,           # ward monsoon rainfall + low-lying/tide exposure
    "facilities": 10,         # hospitals (×2) and schools near the road
    "repeat_complaints": 15,  # non-duplicate complaints on the road
    "repair_failures": 10,    # work orders reopened within 30 days
}
SEVERITY_WEIGHT = {"minor": 1, "serious": 3, "fatal": 6}
FACILITY_RADIUS_M = 600
PLAN_HORIZON_YEARS = 3


def _haversine(lat1, lon1, lat2, lon2):
    r = 6_371_000
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def _norm(s: pd.Series) -> pd.Series:
    m = s.max()
    return s / m if m and m > 0 else s * 0


def priority_scores(roads, traffic, accidents, hotspots, rainfall, tides, facilities, complaints, audit) -> pd.DataFrame:
    df = roads[["road_id", "road_name", "ward_code", "road_class", "under_dlp", "best_bus_route", "bus_routes_count",
                "low_lying", "distress_area_sqm", "centroid_lat", "centroid_lon"]].copy()
    t = traffic.set_index("road_id")
    df["peak_hour_vehicles"] = df.road_id.map(t.peak_hour_vehicles)
    df["congestion_index"] = df.road_id.map(t.congestion_index)
    df["two_wheeler_share"] = df.road_id.map(t.two_wheeler_share)

    acc = accidents[accidents.road_condition_related == "Y"].copy()
    acc["w"] = acc.severity.map(SEVERITY_WEIGHT)
    df["road_condition_accidents"] = df.road_id.map(acc.groupby("road_id").size()).fillna(0).astype(int)
    df["accident_severity_points"] = df.road_id.map(acc.groupby("road_id").w.sum()).fillna(0)
    df["accident_ids"] = df.road_id.map(acc.groupby("road_id").accident_id.apply(list)).map(lambda x: x if isinstance(x, list) else [])

    hs = hotspots.groupby("nearest_road_id").distance_m.min()
    df["flood_hotspot_distance_m"] = df.road_id.map(hs)
    df["flood_hotspot_ids"] = df.road_id.map(hotspots.groupby("nearest_road_id").hotspot_id.apply(list)).map(lambda x: x if isinstance(x, list) else [])
    flood = np.where(df.flood_hotspot_distance_m <= 300, 1.0, np.where(df.flood_hotspot_distance_m <= 700, 0.5, 0.0))

    monsoon = rainfall[pd.to_datetime(rainfall.date).dt.month.isin([6, 7, 8, 9])].groupby("ward_code").rainfall_mm.sum()
    df["ward_monsoon_rain_mm"] = df.ward_code.map(monsoon).round(0)
    tide_alert_days = int((tides.high_tide_alert == "Y").sum())
    rain_tide = 0.5 * _norm(df.ward_monsoon_rain_mm) + 0.5 * (df.low_lying == "Y").astype(float)

    hosp = facilities[facilities.facility_type == "hospital"]
    sch = facilities[facilities.facility_type == "school"]
    def near_count(fac):
        out = []
        for lat, lon in zip(df.centroid_lat, df.centroid_lon):
            d = _haversine(lat, lon, fac.lat.values, fac.lon.values)
            out.append(int((d <= FACILITY_RADIUS_M).sum()))
        return out
    df["hospitals_nearby"] = near_count(hosp)
    df["schools_nearby"] = near_count(sch)

    comp = complaints[complaints.status != "CLOSED_DUPLICATE"]
    df["complaints"] = df.road_id.map(comp.groupby("road_id").size()).fillna(0).astype(int)
    df["reopened_repairs"] = df.road_id.map(audit[audit.reopened_within_30d == "Y"].groupby("road_id").size()).fillna(0).astype(int)

    comps = pd.DataFrame({
        "accidents": _norm(df.accident_severity_points),
        "traffic": 0.6 * _norm(df.peak_hour_vehicles) + 0.4 * (df.congestion_index / 10),
        "bus_exposure": _norm(df.bus_routes_count.astype(float)),
        "flood": flood,
        "rain_tide": rain_tide,
        "facilities": _norm(df.hospitals_nearby * 2 + df.schools_nearby),
        "repeat_complaints": _norm(df.complaints.astype(float)),
        "repair_failures": _norm(df.reopened_repairs.astype(float)),
    })
    for k, w in PRIORITY_WEIGHTS.items():
        df[f"score_{k}"] = (comps[k] * w).round(2)
    df["priority_score"] = sum(df[f"score_{k}"] for k in PRIORITY_WEIGHTS).round(1)
    df["tide_alert_days_citywide"] = tide_alert_days
    return df


def method_durability(audit: pd.DataFrame, rate_card: pd.DataFrame, work_type: str = "pothole_patch") -> pd.DataFrame:
    """Historical durability and lifetime cost per method, from the work-order history."""
    rc = rate_card[rate_card.work_type == work_type].copy()
    hist = audit[audit.work_type == work_type]
    stats = hist.groupby("repair_method").agg(jobs=("work_order_id", "size"),
                                              reopen_rate=("reopened_within_30d", lambda s: (s == "Y").mean()))
    rc = rc.merge(stats, left_on="repair_method", right_index=True, how="left")
    rc["reopen_rate"] = rc.reopen_rate.fillna(0).round(3)
    rc["effective_life_months"] = (rc.expected_life_months * (1 - rc.reopen_rate)).round(1)
    rc["lifetime_cost_per_sqm_year"] = (rc.standard_rate_inr / (rc.effective_life_months / 12)).round(0)
    rc["repairs_in_horizon"] = rc.effective_life_months.map(lambda m: max(1, math.ceil(PLAN_HORIZON_YEARS * 12 / m)))
    return rc.sort_values("lifetime_cost_per_sqm_year").reset_index(drop=True)


def plan(ward_code: str, budget_inr: float, recovered_inr: float, priority: pd.DataFrame,
         durability: pd.DataFrame, held_in_ward_inr: float = 0) -> dict:
    """Greedy, budget-capped plan. Never selects more than budget + recovered."""
    if budget_inr < 0 or recovered_inr < 0:
        raise ValueError("Budget and recovered amount must be non-negative")
    spendable = float(budget_inr) + float(recovered_inr)
    roads = priority[priority.ward_code == ward_code].sort_values(["priority_score", "road_id"], ascending=[False, True])
    best = durability.iloc[0]
    cheapest = durability.sort_values("standard_rate_inr").iloc[0]
    remaining = spendable
    selected, warranty, skipped = [], [], []
    for r in roads.to_dict("records"):
        area = float(r["distress_area_sqm"])
        why = _why(r)
        risk = _risk_evidence(r)
        if r["under_dlp"] == "Y":
            warranty.append(dict(road_id=r["road_id"], road_name=r["road_name"], priority_score=r["priority_score"],
                                 estimated_area_sqm=area, new_bmc_allocation_inr=0,
                                 action="Route to Ward Warranty Desk: identify the original DLP owner before any BMC-funded repair",
                                 counted_as_saving=False,
                                 note="₹0 new BMC allocation is an assumption until the DLP owner is identified; not counted as a confirmed saving.",
                                 why_prioritised=why, risk_evidence=risk))
            continue
        cost = int(round(area * float(best.standard_rate_inr)))
        cheap_cost = int(round(area * float(cheapest.standard_rate_inr)))
        item = dict(road_id=r["road_id"], road_name=r["road_name"], road_class=r["road_class"],
                    priority_score=r["priority_score"], estimated_area_sqm=area,
                    recommended_method=best.repair_method, rate_card_id=best.rate_card_id,
                    estimated_cost_inr=cost,
                    lifetime_cost_3y_inr=int(cost * int(best.repairs_in_horizon)),
                    cheapest_upfront_method=cheapest.repair_method, cheapest_upfront_cost_inr=cheap_cost,
                    cheapest_lifetime_cost_3y_inr=int(cheap_cost * int(cheapest.repairs_in_horizon)),
                    method_durability=dict(reopen_rate_pct=round(float(best.reopen_rate) * 100, 1),
                                           historical_jobs=int(best.jobs) if not pd.isna(best.jobs) else 0,
                                           expected_life_months=int(best.expected_life_months),
                                           effective_life_months=float(best.effective_life_months)),
                    why_prioritised=why, risk_evidence=risk,
                    lat=r["centroid_lat"], lon=r["centroid_lon"])
        if cost <= remaining:
            remaining -= cost
            item["remaining_after_inr"] = int(round(remaining))
            selected.append(item)
        else:
            item["reason_not_selected"] = f"Estimated ₹{cost:,} exceeds remaining ₹{int(remaining):,}"
            skipped.append(item)
    total = sum(s["estimated_cost_inr"] for s in selected)
    assert total <= spendable + 1e-6, "planner exceeded budget"
    return dict(
        ward_code=ward_code, budget_inr=int(budget_inr), recovered_inr=int(recovered_inr),
        spendable_inr=int(spendable), allocated_inr=int(total), remaining_inr=int(round(spendable - total)),
        held_for_review_in_ward_inr=int(held_in_ward_inr),
        held_note="Amounts on Hold for Evidence are not spendable until the hold is resolved; enter only money actually recovered.",
        selected=selected, warranty_routes=warranty, not_selected=skipped[:10],
        method_comparison=durability[["repair_method", "rate_card_id", "standard_rate_inr", "expected_life_months", "reopen_rate",
                                      "effective_life_months", "lifetime_cost_per_sqm_year", "repairs_in_horizon", "jobs"]].to_dict("records"),
        weights=PRIORITY_WEIGHTS,
        methodology=("Roads are ranked by a 0–100 risk score; DLP roads are routed to warranty review at ₹0 new BMC allocation; "
                     f"other roads get the method with the lowest lifetime cost per sqm-year (rate ÷ effective life, where effective life = "
                     f"rate-card life × (1 − historical 30-day reopen rate)). Selection is greedy by priority and stops at the budget."),
    )


def _why(r: dict) -> list[str]:
    out = []
    if r["road_condition_accidents"]:
        out.append(f"{r['road_condition_accidents']} road-condition-related accident(s) recorded")
    if r["peak_hour_vehicles"] >= 2500 or r["congestion_index"] >= 7:
        out.append(f"{int(r['peak_hour_vehicles']):,} peak-hour vehicles, congestion {r['congestion_index']}/10")
    if r["bus_routes_count"]:
        out.append(f"{int(r['bus_routes_count'])} BEST bus route(s)")
    if not pd.isna(r["flood_hotspot_distance_m"]) and r["flood_hotspot_distance_m"] <= 700:
        out.append(f"Flood hotspot {int(r['flood_hotspot_distance_m'])} m away")
    if r["hospitals_nearby"] or r["schools_nearby"]:
        out.append(f"{r['hospitals_nearby']} hospital(s), {r['schools_nearby']} school(s) within {FACILITY_RADIUS_M} m")
    if r["complaints"]:
        out.append(f"{r['complaints']} citizen complaint(s)")
    if r["reopened_repairs"]:
        out.append(f"{r['reopened_repairs']} repair(s) reopened within 30 days")
    return out


def _risk_evidence(r: dict) -> dict:
    return {k: (r[f"score_{k}"]) for k in PRIORITY_WEIGHTS} | {
        "accident_ids": r["accident_ids"][:6], "flood_hotspot_ids": r["flood_hotspot_ids"],
        "two_wheeler_share": r["two_wheeler_share"], "low_lying": r["low_lying"],
    }
