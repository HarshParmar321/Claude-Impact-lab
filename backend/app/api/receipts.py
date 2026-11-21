from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.database import get_session
from app.schemas import AskRequest, FeedbackRequest
from app.services import receipt_service
from app.services.data_store import get_store

router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.get("/{work_order_id}")
def get_receipt(work_order_id: str, language: str = "en", session: Session = Depends(get_session)):
    r = receipt_service.receipt(get_store(), session, work_order_id, language)
    if r is None:
        raise HTTPException(404, f"Work order {work_order_id} not found")
    return r


@router.post("/{work_order_id}/durability-feedback")
def durability_feedback(work_order_id: str, body: FeedbackRequest, session: Session = Depends(get_session)):
    try:
        return receipt_service.submit_feedback(get_store(), session, work_order_id, body.answer, body.description,
                                               body.language, body.photo_reference)
    except KeyError:
        raise HTTPException(404, f"Work order {work_order_id} not found")


@router.post("/{work_order_id}/ask")
def ask(work_order_id: str, body: AskRequest, session: Session = Depends(get_session)):
    try:
        return receipt_service.ask(get_store(), session, work_order_id, body.question, body.language)
    except KeyError:
        raise HTTPException(404, f"Work order {work_order_id} not found")
