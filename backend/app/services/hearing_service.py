"""Claude Fair Hearing with cache and deterministic fallback (spec §10).

Order: live Claude (if key) → committed/runtime cache by evidence hash → template.
The UI never becomes unusable because Claude is unavailable.
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone

from pydantic import ValidationError
from sqlmodel import Session

from app import config
from app.models import HearingCacheMetadata
from app.schemas import HearingOutput, contains_forbidden
from app.services import claude_service
from app.templates.hearing_fallback import build_template_hearing

_lock = threading.Lock()


def build_evidence(case: dict) -> dict:
    """Structured, Python-computed evidence only. This is all Claude sees."""
    wo = case["work_order"]
    dup = case["duplicate"]
    ctx = case["context"]
    return {
        "work_order": wo,
        "complaints": [{k: c[k] for k in ("complaint_id", "created_at", "language", "text_original", "text_en", "category",
                                          "status", "duplicate_of", "linked_work_order_id", "upvotes")} for c in case["complaints"]],
        "rate_check": {k: v for k, v in case["rate_check"].items() if k != "thresholds"}
                      | {"thresholds": "<0.75 low-cost/data-quality outlier; 0.75–1.30 normal; >1.30–1.40 context band; >1.40 review lead"},
        "duplicate_comparison": None if not dup else {k: dup[k] for k in ("role", "flagged_id", "partner_id", "days_apart", "area_diff_pct",
                                                                         "cost_diff_pct", "same_contractor", "criteria", "label")}
                                | {"partner_facts": [x for x in dup["side_by_side"] if x["work_order_id"] != wo["work_order_id"]][0]},
        "dlp": case["dlp"],
        "sla_and_reopen": {"sla_tier": wo["sla_tier"], "sla_days": wo["sla_days"], "sla_met": wo["sla_met"],
                           "reopened_within_30d": wo["reopened_within_30d"]},
        "evidence_completeness": case["evidence_completeness"],
        "context": {
            "traffic": ctx["traffic"],
            "road": ctx["road"],
            "accidents": [a for a in ctx["accidents"] if a["road_condition_related"]],
            "flood_hotspots": ctx["flood_hotspots"],
            "rainfall": ctx["rainfall"],
            "tide_alerts": ctx["tide_alerts"],
            "social_posts": ctx["social_posts"],
        },
        "record_conflicts": case["record_conflicts"],
        "rules_triggered": case["rules"],
        "rule_based_verdict": case["recommended_verdict"],
        "verdict_precedence": case["verdict_precedence"],
        "rule_based_evidence_required": case["evidence_required"],
        "lead_confidence": case["confidence"],
        "data_limitations": case["data_limitations"],
        "source_ids": case["source_ids"],
    }


def evidence_hash(evidence: dict) -> str:
    canon = json.dumps(evidence, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def load_cache() -> dict:
    if not config.CACHE_PATH.exists():
        return {"entries": {}}
    try:
        return json.loads(config.CACHE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"entries": {}}


def _save_cache_entry(h: str, wo_id: str, output: dict, origin: str) -> None:
    with _lock:
        data = load_cache()
        data.setdefault("entries", {})[h] = {"work_order_id": wo_id, "origin": origin,
                                            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                            "response": output}
        config.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        config.CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_output(raw: dict, evidence: dict) -> tuple[dict | None, list[str]]:
    """Schema + language + source-ID checks. Returns (output, problems)."""
    problems: list[str] = []
    try:
        out = HearingOutput.model_validate(raw).model_dump()
    except ValidationError as e:
        return None, [f"schema: {err['loc']} {err['msg']}" for err in e.errors()[:5]]
    bad = contains_forbidden(json.dumps(out, ensure_ascii=False))
    if bad:
        problems.append(f"forbidden wording: {bad}")
    allowed = set(evidence["source_ids"])
    cited = set(out["auditor_case"]["source_ids"]) | set(out["fairness_case"]["source_ids"])
    invented = sorted(cited - allowed)
    if invented:
        problems.append(f"source IDs not in evidence: {invented}")
    if not out["auditor_case"]["source_ids"]:
        problems.append("auditor case cites no source IDs")
    return (None if problems else out), problems


def run_hearing(case: dict, session: Session, *, force_template: bool = False) -> dict:
    evidence = build_evidence(case)
    h = evidence_hash(evidence)
    wo_id = case["work_order"]["work_order_id"]
    notes: list[str] = []
    output, mode, origin = None, None, None

    if not force_template and config.live_claude_enabled():
        try:
            raw = claude_service.run_fair_hearing(evidence)
            output, problems = validate_output(raw, evidence)
            if output:
                mode, origin = "live", f"live:{config.ANTHROPIC_MODEL}"
                _save_cache_entry(h, wo_id, output, origin)
            else:
                notes.append("Live response rejected by validation: " + "; ".join(problems))
        except (claude_service.ClaudeUnavailable, ValueError, json.JSONDecodeError) as e:
            notes.append(f"Live Claude unavailable: {str(e)[:160]}")
    elif not config.live_claude_enabled():
        notes.append("No ANTHROPIC_API_KEY configured; using cache or template.")

    if output is None and not force_template:
        entry = load_cache().get("entries", {}).get(h)
        if entry:
            cand, problems = validate_output(entry["response"], evidence)
            if cand:
                output, mode, origin = cand, "cache", entry.get("origin", "cache")
            else:
                notes.append("Cached response failed validation: " + "; ".join(problems))

    if output is None:
        output, mode, origin = build_template_hearing(evidence), "template", "deterministic template"

    session.add(HearingCacheMetadata(work_order_id=wo_id, evidence_hash=h, mode=mode))
    session.commit()

    return {
        **output,
        "mode": mode,
        "origin": origin,
        "evidence_hash": h,
        "rule_based_verdict": case["recommended_verdict"],
        "verdict_differs_from_rules": output["recommended_verdict"] != case["recommended_verdict"],
        "supplied_source_ids": evidence["source_ids"],
        "notes": notes,
    }
