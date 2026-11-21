"""Fair contractor and ward scorecards (spec §8). Deterministic pandas only."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

MIN_SAMPLE_HIGH = 30
MIN_SAMPLE_MEDIUM = 10

CONTRACTOR_DIMENSIONS = {
    "sla_reliability": "Share of jobs completed within the SLA tier's allowed days",
    "durability": "Share of jobs NOT reopened within 30 days",
    "rate_alignment": "Share of billed jobs within 0.75×–1.30× of the rate card",
    "evidence_completeness": "Average share of before photo, after photo, measurement book and completion certificate present",
}

WARD_DIMENSIONS = {
    "linkage": "Share of work orders that cite a citizen complaint",
    "dlp_control": "Share of work orders on DLP roads executed under warranty at ₹0 to BMC",
    "duplicate_control": "100 − 10 × (duplicate-like records as % of billed work orders), floored at 0",
    "sla_oversight": "Share of the ward's work orders completed within SLA",
    "risk_allocation": "Share of ward repair spend on roads in the ward's higher-risk half (planner priority score)",
}


def sample_confidence(n: int) -> str:
    if n >= MIN_SAMPLE_HIGH:
        return "HIGH"
    if n >= MIN_SAMPLE_MEDIUM:
        return "MEDIUM"
    return "LOW"


def _dimension_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["sla"] = (df.sla_met == "Y").astype(float)
    out["durable"] = (df.reopened_within_30d != "Y").astype(float)
    billed = df.cost_inr > 0
    out["rate_ok"] = np.where(billed, (df.rate_band == "NORMAL").astype(float), np.nan)
    ev = df[["photo_before", "photo_after", "measurement_book", "engineer_certificate"]].eq("Y").mean(axis=1)
    out["evidence"] = ev
    return out


def contractor_scorecards(audit: pd.DataFrame, contractors: pd.DataFrame) -> list[dict]:
    """Compare each contractor with peers doing the same repair method in the same SLA tier.

    DLP review leads and duplicate-like records are NOT scored against the
    contractor (warranty ownership and intent are not established); they are
    listed separately as open review leads.
    """
    df = audit.copy()
    dims = _dimension_frame(df)
    df = pd.concat([df, dims], axis=1)
    df["peer_group"] = df.repair_method + " · " + df.sla_tier
    peer = df.groupby("peer_group").agg(peer_n=("work_order_id", "size"), peer_contractors=("contractor_id", "nunique"),
                                         p_sla=("sla", "mean"), p_dur=("durable", "mean"), p_rate=("rate_ok", "mean"),
                                         p_ev=("evidence", "mean"))
    names = contractors.set_index("contractor_id").contractor_name
    results = []
    for cid, g in df.groupby("contractor_id"):
        groups = []
        for pg, gg in g.groupby("peer_group"):
            p = peer.loc[pg]
            n = len(gg)
            groups.append(dict(
                peer_group=pg, repair_method=gg.repair_method.iloc[0], sla_tier=gg.sla_tier.iloc[0],
                sample_size=n, peer_sample_size=int(p.peer_n), peer_contractors=int(p.peer_contractors),
                confidence=sample_confidence(n), low_sample_warning=n < MIN_SAMPLE_MEDIUM,
                sla_reliability=_pct(gg.sla.mean()), peer_sla_reliability=_pct(p.p_sla),
                durability=_pct(gg.durable.mean()), peer_durability=_pct(p.p_dur),
                rate_alignment=_pct(gg.rate_ok.mean()), peer_rate_alignment=_pct(p.p_rate),
                evidence_completeness=_pct(gg.evidence.mean()), peer_evidence_completeness=_pct(p.p_ev),
            ))
        n = len(g)
        dims_raw = {
            "sla_reliability": _pct(g.sla.mean()),
            "durability": _pct(g.durable.mean()),
            "rate_alignment": _pct(g.rate_ok.mean()),
            "evidence_completeness": _pct(g.evidence.mean()),
        }
        # Sample-weighted gap versus each peer group's average (positive = better than comparable jobs)
        gaps = {}
        for key, col, pcol in (("sla_reliability", "sla", "p_sla"), ("durability", "durable", "p_dur"),
                                ("rate_alignment", "rate_ok", "p_rate"), ("evidence_completeness", "evidence", "p_ev")):
            vals = []
            weights = []
            for pg, gg in g.groupby("peer_group"):
                v = gg[col].mean()
                if pd.isna(v) or pd.isna(peer.loc[pg, pcol]):
                    continue
                vals.append((v - peer.loc[pg, pcol]) * 100)
                weights.append(len(gg))
            gaps[key] = round(float(np.average(vals, weights=weights)), 1) if vals else None
        overall = round(float(np.mean([v for v in dims_raw.values() if v is not None])), 1)
        open_leads = g[g.is_review_lead]
        results.append(dict(
            contractor_id=cid, contractor_name=str(names.get(cid, cid)), sample_size=n,
            confidence=sample_confidence(n), overall_score=overall, dimensions=dims_raw, gap_vs_peers=gaps,
            peer_groups=sorted(groups, key=lambda x: -x["sample_size"]),
            open_review_leads=dict(
                count=int(len(open_leads)),
                dlp_review_not_attributed=int(open_leads.rules.map(lambda r: "DLP_REVIEW" in r).sum()),
                possible_duplicates_not_scored=int(open_leads.rules.map(lambda r: "POSSIBLE_DUPLICATE" in r).sum()),
                rate_card_leads=int(open_leads.rules.map(lambda r: "RATE_CARD_REVIEW" in r).sum()),
            ),
            evidence_links=dict(
                sla_breaches=g[g.sla == 0].work_order_id.head(8).tolist(),
                reopened=g[g.durable == 0].work_order_id.head(8).tolist(),
                outside_rate_range=g[(g.rate_ok == 0)].work_order_id.head(8).tolist(),
            ),
        ))
    return sorted(results, key=lambda x: x["contractor_id"])


CATEGORY_KEYWORDS = {
    "drain_cover": re.compile(r"drain cover|manhole|cover (is )?(missing|open|broken)", re.I),
    "waterlogging": re.compile(r"water ?logging", re.I),
    "pothole": re.compile(r"pothole", re.I),
    "road_surface": re.compile(r"trench|surface .*broken|broken after", re.I),
}


def text_category(text_en: str) -> str | None:
    for cat, rx in CATEGORY_KEYWORDS.items():
        if rx.search(text_en or ""):
            return cat
    return None


def category_conflicts(complaints: pd.DataFrame) -> pd.DataFrame:
    """Complaints whose English text describes a different issue than their category."""
    detected = complaints.text_en.map(text_category)
    mask = detected.notna() & (detected != complaints.category)
    out = complaints[mask][["complaint_id", "ward_code", "road_id", "category", "status", "duplicate_of"]].copy()
    out["text_suggests"] = detected[mask]
    return out


def ward_scorecards(audit: pd.DataFrame, complaints: pd.DataFrame, wards: pd.DataFrame,
                    priority: pd.DataFrame) -> list[dict]:
    conflicts = category_conflicts(complaints)
    prio = priority.set_index("road_id")
    results = []
    for _, w in wards.iterrows():
        g = audit[audit.ward_code == w.ward_code]
        billed = g[g.cost_inr > 0]
        n = len(g)
        linkage = _pct((g.complaint_id != "").mean())
        dlp_wos = g[g.road_under_dlp == "Y"]
        dlp_control = _pct((dlp_wos.cost_inr == 0).mean()) if len(dlp_wos) else None
        dup_count = int(g.rules.map(lambda r: "POSSIBLE_DUPLICATE" in r).sum())
        dup_rate = dup_count / max(1, len(billed)) * 100
        dup_control = round(max(0.0, 100 - 10 * dup_rate), 1)
        sla = _pct((g.sla_met == "Y").mean())
        ward_roads = prio[prio.ward_code == w.ward_code]
        median = ward_roads.priority_score.median()
        high_roads = set(ward_roads[ward_roads.priority_score >= median].index)
        spend = billed.cost_inr.sum()
        risk_alloc = _pct(billed[billed.road_id.isin(high_roads)].cost_inr.sum() / spend) if spend else None
        dims = dict(linkage=linkage, dlp_control=dlp_control, duplicate_control=dup_control,
                    sla_oversight=sla, risk_allocation=risk_alloc)
        overall = round(float(np.mean([v for v in dims.values() if v is not None])), 1)
        wc = conflicts[conflicts.ward_code == w.ward_code]
        dlp_paid = g[g.rules.map(lambda r: "DLP_REVIEW" in r)]
        results.append(dict(
            ward_code=w.ward_code, ward_name=w.ward_name, zone=w.zone, sample_size=n,
            confidence=sample_confidence(n), overall_score=overall, dimensions=dims,
            metrics=dict(
                work_orders=n, billed_work_orders=int(len(billed)), billed_amount_inr=int(spend),
                dlp_road_work_orders=int(len(dlp_wos)), duplicate_like_records=dup_count,
                unique_review_leads=int(g.is_review_lead.sum()),
                amount_requiring_review_inr=int(g[g.is_review_lead].cost_inr.sum()),
            ),
            attribution=dict(
                contractor_delivery=dict(
                    sla_breaches=int((g.sla_met != "Y").sum()),
                    reopened_within_30d=int((g.reopened_within_30d == "Y").sum()),
                    evidence_gaps=int((g[["photo_before", "photo_after", "measurement_book", "engineer_certificate"]] != "Y").any(axis=1).sum()),
                ),
                ward_system=dict(
                    work_orders_without_complaint=int((g.complaint_id == "").sum()),
                    dlp_road_payments=int(len(dlp_paid)),
                    dlp_road_payments_inr=int(dlp_paid.cost_inr.sum()),
                    duplicate_like_records=dup_count,
                ),
                data_quality=dict(
                    low_cost_outliers=int(g.rules.map(lambda r: "LOW_COST_DATA_QUALITY" in r).sum()),
                    complaint_category_conflicts=int(len(wc)),
                ),
            ),
            evidence_links=dict(
                dlp_road_payments=dlp_paid.work_order_id.head(8).tolist(),
                duplicate_like=g[g.rules.map(lambda r: "POSSIBLE_DUPLICATE" in r)].work_order_id.head(8).tolist(),
                missing_complaint=g[g.complaint_id == ""].work_order_id.head(8).tolist(),
                category_conflicts=wc.complaint_id.head(8).tolist(),
            ),
        ))
    return results


def _pct(v) -> float | None:
    if v is None or pd.isna(v):
        return None
    return round(float(v) * 100, 1)
