# NagarLens architecture

```text
frontend (Next.js, :3000)                         backend (FastAPI, :8000, prefix /api)
┌──────────────────────────────┐   TanStack     ┌───────────────────────────────────────────────┐
│ /            Overview         │   Query        │ api/summary.py     GET /health, /summary       │
│ /reviews     Review Inbox     │ ─────────────▶ │ api/reviews.py     GET /reviews, /reviews/{id} │
│ /reviews/[id] Case + Hearing  │   JSON         │                    POST /reviews/{id}/hearing  │
│ /scorecards  Contractors/Wards│ ◀───────────── │                    PATCH /reviews/{id}/verdict │
│ /planner     Next-Rupee       │  snake_case →  │ api/scorecards.py  GET /scorecards/...         │
│ /receipt/[id] Public Receipt  │  camelCase in  │ api/planner.py     GET /planner/recommendations│
└──────────────────────────────┘  lib/api.ts    │ api/receipts.py    GET/POST /receipts/...      │
                                                └───────────────┬───────────────────────────────┘
                                                                │
              services/ (adapters)                              ▼
  data_store.py ── loads CSV/GeoJSON once, runs the audit, caches derived tables
  audit_adapter.py ── leads, case detail, record conflicts, timeline, overview, decisions
  scorecard_adapter.py ── contractor (peer-group) and ward scorecards
  budget_adapter.py ── budget-capped planner
  hearing_service.py ── evidence package → live Claude → cache → template; validation
  claude_service.py ── the ONLY module that calls the Anthropic SDK
  receipt_service.py ── multilingual receipt, durability feedback, citizen Q&A

  calculations/ (pure pandas, deterministic)
  audit.py · scorecards.py · budget.py

  SQLite (SQLModel): OfficerDecision · DurabilityFeedback · HearingCacheMetadata
```

## Principles enforced in code

| Principle | Where |
|---|---|
| Evidence before accusation | Forbidden-word validation on every Claude output (`schemas.contains_forbidden`); template wording; conflicts phrased as "requires verification" |
| Deterministic calculations before AI | `calculations/*`; Claude receives computed figures and source IDs only (`hearing_service.build_evidence`) |
| Fair peer comparisons | Contractor scores per (repair method × SLA tier) with sample size, peer sample and low-sample warning |
| System vs contractor failures | Ward attribution split: contractor delivery / ward-system / data quality; DLP and unresolved duplicates are not scored against contractors |
| Every flag leads to an action | Verdict precedence in `audit.initial_verdict`; evidence checklist from `audit.evidence_required` |
| Traceable to source records | Every case lists `source_ids`; Claude outputs citing IDs outside the evidence are rejected |
| Works without an API key | `hearing_service.run_hearing` fallback chain; `/api/health` reports `claude_mode` |

## Fair Hearing validation

A Claude response is accepted only if it:

1. Parses as JSON and matches the `HearingOutput` schema (spec §10).
2. Contains none of: fraud, corrupt, scam, guilty, stole(n).
3. Cites only source IDs present in the supplied evidence, and the auditor case cites at least one.

Otherwise the next fallback is used. Every hearing run is logged in `HearingCacheMetadata` with its mode and evidence hash.

## Planner

Priority score (0–100) weights: accidents 25, traffic 15, BEST bus exposure 10, flood proximity 10, rain + tide 5, hospitals/schools 10, repeat complaints 15, repair failures 10. DLP roads are routed to the Ward Warranty Desk at an assumed ₹0 new BMC allocation and are **not** counted as savings. Other roads get the method with the lowest lifetime cost per sqm-year (rate ÷ effective life, where effective life = rate-card life × (1 − historical 30-day reopen rate)). Selection is greedy by priority and asserts `allocated ≤ budget + recovered`.
