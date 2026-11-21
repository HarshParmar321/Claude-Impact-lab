from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.database import get_session
from app.schemas import VerdictRequest
from app.services import audit_adapter, hearing_service
from app.services.data_store import get_store

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("")
def list_reviews(
    ward: Optional[str] = None,
    contractor: Optional[str] = None,
    rule: Optional[str] = None,
    verdict: Optional[str] = None,
    repair_method: Optional[str] = None,
    include_data_quality: bool = False,
    q: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    return audit_adapter.list_leads(get_store(), session, ward=ward, contractor=contractor, rule=rule, verdict=verdict,
                                    repair_method=repair_method, include_data_quality=include_data_quality, q=q,
                                    limit=limit, offset=offset)


@router.get("/{work_order_id}")
def get_review(work_order_id: str, session: Session = Depends(get_session)):
    case = audit_adapter.build_case(get_store(), session, work_order_id)
    if case is None:
        raise HTTPException(404, f"Work order {work_order_id} not found")
    return case


@router.post("/{work_order_id}/hearing")
def fair_hearing(work_order_id: str, force_template: bool = False, session: Session = Depends(get_session)):
    case = audit_adapter.build_case(get_store(), session, work_order_id)
    if case is None:
        raise HTTPException(404, f"Work order {work_order_id} not found")
    return hearing_service.run_hearing(case, session, force_template=force_template)


@router.patch("/{work_order_id}/verdict")
def save_verdict(work_order_id: str, body: VerdictRequest, session: Session = Depends(get_session)):
    try:
        d = audit_adapter.record_decision(get_store(), session, work_order_id, body.verdict, body.officer_reason)
    except KeyError:
        raise HTTPException(404, f"Work order {work_order_id} not found")
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"decision": d.model_dump(mode="json")}
