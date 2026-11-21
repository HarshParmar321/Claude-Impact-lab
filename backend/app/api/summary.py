from fastapi import APIRouter, Depends
from sqlmodel import Session

from app import config
from app.database import get_session
from app.services import audit_adapter, scorecard_adapter
from app.services.data_store import get_store
from app.services.hearing_service import load_cache

router = APIRouter(tags=["overview"])


@router.get("/health")
def health():
    try:
        store = get_store()
        loaded = len(store.work_orders) > 0
    except Exception:  # pragma: no cover
        loaded = False
    if config.live_claude_enabled():
        mode = "live"
    elif load_cache().get("entries"):
        mode = "cache"
    else:
        mode = "template"
    return {"status": "ok", "data_loaded": loaded, "claude_mode": mode,
            "model": config.ANTHROPIC_MODEL if config.live_claude_enabled() else None}


@router.get("/summary")
def summary(session: Session = Depends(get_session)):
    return audit_adapter.overview(get_store(), session, scorecard_adapter.ward_cards(), scorecard_adapter.contractor_cards())
