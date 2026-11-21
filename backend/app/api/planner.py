from fastapi import APIRouter, HTTPException, Query

from app.services import budget_adapter
from app.services.data_store import get_store

router = APIRouter(prefix="/planner", tags=["planner"])


@router.get("/recommendations")
def recommendations(ward_code: str, budget_inr: float = Query(..., ge=0, le=1_000_000_000),
                    recovered_inr: float = Query(0, ge=0, le=1_000_000_000)):
    try:
        return budget_adapter.recommendations(ward_code, budget_inr, recovered_inr)
    except KeyError:
        raise HTTPException(404, f"Ward {ward_code} not found")


@router.get("/wards")
def wards():
    s = get_store()
    return {"items": s.wards[["ward_code", "ward_name", "annual_road_budget_inr"]].to_dict("records")}
