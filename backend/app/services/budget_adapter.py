from __future__ import annotations

from app.calculations import budget as budget_calc
from app.services.data_store import get_store


def recommendations(ward_code: str, budget_inr: float, recovered_inr: float = 0) -> dict:
    s = get_store()
    if ward_code not in set(s.wards.ward_code):
        raise KeyError(ward_code)
    a = s.audit
    held = a[(a.ward_code == ward_code) & (a.recommended_verdict == "HOLD_FOR_EVIDENCE") & a.is_review_lead].cost_inr.sum()
    return budget_calc.plan(ward_code, budget_inr, recovered_inr, s.priority, s.durability, held_in_ward_inr=float(held))
