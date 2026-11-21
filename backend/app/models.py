"""SQLite persistence (spec §18). The generated database file is git-ignored."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OfficerDecision(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    work_order_id: str = Field(index=True)
    recommended_verdict: str
    final_verdict: str
    is_override: bool = False
    officer_reason: str
    created_at: datetime = Field(default_factory=_now)


class DurabilityFeedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    work_order_id: str = Field(index=True)
    answer: str  # SURVIVED | FAILED | UNSURE
    description: str = ""
    photo_reference: str = ""  # placeholder reference only; no image verification is performed
    language: str = "en"
    created_at: datetime = Field(default_factory=_now)
    generated_warranty_review: bool = False
    routed_to: str = ""
    case_reference: str = ""


class HearingCacheMetadata(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    work_order_id: str = Field(index=True)
    evidence_hash: str
    mode: str  # live | cache | template
    created_at: datetime = Field(default_factory=_now)
