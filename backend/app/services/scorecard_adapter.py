"""Wraps scorecard calculations; results are cached because the dataset is static."""

from __future__ import annotations

from functools import lru_cache

from app.calculations import scorecards as sc
from app.services.data_store import get_store


@lru_cache(maxsize=1)
def contractor_cards() -> list[dict]:
    s = get_store()
    return sc.contractor_scorecards(s.audit, s.contractors)


@lru_cache(maxsize=1)
def ward_cards() -> list[dict]:
    s = get_store()
    return sc.ward_scorecards(s.audit, s.complaints, s.wards, s.priority)


def methodology() -> dict:
    return {
        "contractor_dimensions": sc.CONTRACTOR_DIMENSIONS,
        "ward_dimensions": sc.WARD_DIMENSIONS,
        "peer_group": "Same repair method and same SLA tier. Sample size and peer sample shown for every comparison.",
        "confidence": f"HIGH ≥ {sc.MIN_SAMPLE_HIGH} jobs · MEDIUM ≥ {sc.MIN_SAMPLE_MEDIUM} · LOW otherwise (low-sample warning)",
        "not_scored_against_contractors": "DLP review leads (warranty owner unknown) and duplicate-like records (unresolved) are listed but not scored.",
    }
