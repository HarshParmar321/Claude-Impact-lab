"""Pydantic request/response contracts. API JSON is snake_case; the frontend
converts keys to camelCase in one place (frontend/lib/api.ts)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Verdict = Literal["RELEASE_PAYMENT", "HOLD_FOR_EVIDENCE", "WARRANTY_REVIEW"]
Confidence = Literal["HIGH", "MEDIUM", "LOW"]
Language = Literal["en", "mr", "hi", "hinglish"]

FORBIDDEN_WORDS = ("fraud", "corrupt", "scam", "guilty", "stole", "stolen")


def contains_forbidden(text: str) -> list[str]:
    low = text.lower()
    return [w for w in FORBIDDEN_WORDS if w in low]


class AuditorCase(BaseModel):
    summary: str
    evidence: list[str]
    source_ids: list[str]


class FairnessCase(BaseModel):
    possible_legitimate_context: list[str]
    limitations: list[str]
    source_ids: list[str]


class HearingOutput(BaseModel):
    """Exact Fair Hearing schema from spec §10."""

    auditor_case: AuditorCase
    fairness_case: FairnessCase
    recommended_verdict: Verdict
    reasoning: str
    evidence_required: list[str]
    citizen_explanation: str
    officer_brief: str
    confidence: Confidence


class VerdictRequest(BaseModel):
    verdict: Verdict
    officer_reason: str = Field(default="", max_length=1000)

    @field_validator("officer_reason")
    @classmethod
    def strip(cls, v: str) -> str:
        return v.strip()


class FeedbackRequest(BaseModel):
    answer: Literal["SURVIVED", "FAILED", "UNSURE"]
    description: str = Field(default="", max_length=1000)
    language: Language = "en"
    photo_reference: str = Field(default="", max_length=200)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    language: Language = "en"
