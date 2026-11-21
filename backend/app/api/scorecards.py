from fastapi import APIRouter, HTTPException

from app.services import scorecard_adapter

router = APIRouter(prefix="/scorecards", tags=["scorecards"])


@router.get("/contractors")
def contractors():
    return {"items": scorecard_adapter.contractor_cards(), "methodology": scorecard_adapter.methodology()}


@router.get("/contractors/{contractor_id}")
def contractor(contractor_id: str):
    for c in scorecard_adapter.contractor_cards():
        if c["contractor_id"] == contractor_id:
            return c | {"methodology": scorecard_adapter.methodology()}
    raise HTTPException(404, f"Contractor {contractor_id} not found")


@router.get("/wards")
def wards():
    return {"items": scorecard_adapter.ward_cards(), "methodology": scorecard_adapter.methodology()}


@router.get("/wards/{ward_code:path}")
def ward(ward_code: str):
    for w in scorecard_adapter.ward_cards():
        if w["ward_code"] == ward_code:
            return w | {"methodology": scorecard_adapter.methodology()}
    raise HTTPException(404, f"Ward {ward_code} not found")
