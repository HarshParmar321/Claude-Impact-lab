"""The only place the Anthropic SDK is called. The browser never talks to Anthropic."""

from __future__ import annotations

import json
import re

from app import config

HEARING_SYSTEM_PROMPT = """You are the fairness layer in a civic road-repair payment review system.

Use only the supplied structured evidence. Never invent an amount, date,
record ID, contractor relationship, photograph, legal finding or causal link.

First present the strongest evidence for review as the Auditor. Then present
the strongest reasonable context or limitation as the Fairness Advocate.
Finally recommend exactly one verdict: RELEASE_PAYMENT, HOLD_FOR_EVIDENCE,
or WARRANTY_REVIEW.

Never use the words fraud, corrupt, scam, guilty or stolen. A flag is a review
lead, not proof of intent. If the road is under DLP but the original warranty
contractor is unknown, assign the unresolved control issue to the Ward
Warranty Desk, not automatically to the current contractor.

Return valid JSON only and include the supplied source IDs supporting each
claim. If evidence is insufficient, say so explicitly."""

OUTPUT_SCHEMA_HINT = {
    "auditor_case": {"summary": "", "evidence": [], "source_ids": []},
    "fairness_case": {"possible_legitimate_context": [], "limitations": [], "source_ids": []},
    "recommended_verdict": "RELEASE_PAYMENT | HOLD_FOR_EVIDENCE | WARRANTY_REVIEW",
    "reasoning": "",
    "evidence_required": [],
    "citizen_explanation": "",
    "officer_brief": "",
    "confidence": "HIGH | MEDIUM | LOW",
}

CITIZEN_SYSTEM_PROMPT = """You answer a citizen's question about one road repair in Mumbai.
Use only the supplied repair receipt facts. Answer in the requested language
(en = English, mr = Marathi in Devanagari, hi = Hindi in Devanagari,
hinglish = Hindi in Latin script). Keep it under 90 words, plain and polite.
Never use the words fraud, corrupt, scam, guilty or stolen. A review lead is not
proof of wrongdoing. Do not invent dates, amounts or names. Return plain text only."""


class ClaudeUnavailable(Exception):
    pass


def _client():
    if not config.live_claude_enabled():
        raise ClaudeUnavailable("No API key configured (or live calls disabled)")
    try:
        import anthropic
    except ImportError as e:  # pragma: no cover
        raise ClaudeUnavailable("anthropic SDK not installed") from e
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, timeout=config.ANTHROPIC_TIMEOUT_S, max_retries=1)


def _text(resp) -> str:
    return "".join(getattr(b, "text", "") for b in resp.content)


def extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object in response")
    return json.loads(text[start: end + 1])


def run_fair_hearing(evidence: dict) -> dict:
    client = _client()
    user = (
        "Structured evidence for one review lead (all calculations were produced by Python and are authoritative):\n"
        + json.dumps(evidence, ensure_ascii=False, indent=1)
        + "\n\nThe rule-based initial recommendation follows the precedence in `verdict_precedence`. If you recommend a "
          "different verdict, explain why in `reasoning`.\nReturn ONLY a JSON object with exactly this shape:\n"
        + json.dumps(OUTPUT_SCHEMA_HINT, indent=1)
    )
    try:
        resp = client.messages.create(model=config.ANTHROPIC_MODEL, max_tokens=2500, system=HEARING_SYSTEM_PROMPT,
                                      messages=[{"role": "user", "content": user}])
    except Exception as e:  # network, auth, rate limit, model not found…
        raise ClaudeUnavailable(f"{type(e).__name__}: {e}") from e
    return extract_json(_text(resp))


def answer_citizen(question: str, language: str, facts: dict) -> str:
    client = _client()
    user = f"Language: {language}\nReceipt facts:\n{json.dumps(facts, ensure_ascii=False, indent=1)}\n\nCitizen question: {question}"
    try:
        resp = client.messages.create(model=config.ANTHROPIC_MODEL, max_tokens=400, system=CITIZEN_SYSTEM_PROMPT,
                                      messages=[{"role": "user", "content": user}])
    except Exception as e:
        raise ClaudeUnavailable(f"{type(e).__name__}: {e}") from e
    return _text(resp).strip()
