# NagarLens — Claude Build Specification

## Evidence-to-Action Accountability for Mumbai Road Repairs

This document is the implementation brief for Claude. Build the product described here without changing its core workflow, audit rules, fairness safeguards, or technology stack.

---

## 1. Product Definition

**Product name:** NagarLens  
**Feature module:** RupeeProof Action Layer  
**Tagline:** **Find the evidence. Hear both sides. Act on every rupee.**

NagarLens connects citizen complaints, work orders, roads, contractors, rate cards, wards, repair outcomes and public-risk data. It produces accurate audit review leads, fair contractor and ward scorecards, and budget-capped recommendations for where the next rupee should go.

The RupeeProof Action Layer turns each review lead into something a ward officer and citizen can act on:

```text
NagarLens Review Lead
        ↓
Claude Fair Hearing
        ↓
Release Payment | Hold for Evidence | Warranty Review
        ↓
Public Repair Receipt
        ↓
Citizen: “Did this repair survive?”
        ↓
Failed repair returns to warranty review
```

The product must never declare fraud or corruption. It must use phrases such as **review lead**, **record conflict**, **supporting evidence required**, and **warranty verification required**.

---

## 2. Primary Users

### Ward officer

Needs to:

- See which payments need review and why.
- Inspect the complete complaint-to-payment trail.
- Compare contractor performance fairly.
- Request the exact evidence required to clear a flag.
- Decide whether to release, hold or route a case to warranty review.
- Reinvest available budget into the highest-priority roads.

### Citizen

Needs to:

- Ask what happened to a complaint in Marathi, Hindi, Hinglish or English.
- View a plain-language Public Repair Receipt.
- See the repair date, cost, contractor, current status and warranty state.
- Report whether the completed repair survived.

### Corporator or auditor

Needs to:

- Compare wards and contractors using explainable scorecards.
- Inspect the evidence behind every score.
- Understand system failures separately from contractor performance.

---

## 3. Judging-Criteria Coverage

| Criterion | Weight | Required product evidence |
|---|---:|---|
| Audit accuracy | 25% | Explicit rate thresholds, duplicate detection, DLP checks, deduplicated lead counts and record-level evidence |
| Fair accountability | 20% | Peer-group comparison, system-versus-contractor separation and Claude Fair Hearing |
| Budget smarts | 20% | Budget-capped recommendations based on lifetime cost and public risk |
| Connects the trail | 15% | Complaint → issue → work order → road → rate card → ward → verdict |
| Usable + demo | 20% | Officer decision workflow, multilingual citizen answer and Public Repair Receipt |

---

## 4. Fixed Technology Stack

Do not replace this stack unless a dependency is impossible to use.

| Layer | Choice |
|---|---|
| Frontend | Next.js + TypeScript |
| UI | Tailwind CSS + shadcn/ui |
| Charts | Recharts, including Sankey |
| Maps | Leaflet with `react-leaflet` |
| Data fetching | TanStack Query |
| Backend | FastAPI + Pydantic + Uvicorn |
| Calculations | pandas; preserve Kshitij's existing calculation modules |
| Database | SQLite through SQLModel |
| AI | Anthropic Python SDK, called only by the backend |
| Repository | One public GitHub repository containing `frontend/` and `backend/` |
| Local runtime | Frontend on `localhost:3000`; backend on `localhost:8000` |

Important: a Claude Max subscription can be used for development with Claude, but it does not automatically provide Anthropic API credits. Runtime SDK calls require an Anthropic API key with API access. The committed JSON cache and deterministic template fallback must make the demo work without an API key.

---

## 5. Repository Structure

```text
nagarlens/
├── README.md
├── .gitignore
├── frontend/
│   ├── .env.local.example
│   ├── package.json
│   ├── app/
│   │   ├── page.tsx
│   │   ├── reviews/page.tsx
│   │   ├── reviews/[workOrderId]/page.tsx
│   │   ├── scorecards/page.tsx
│   │   ├── planner/page.tsx
│   │   └── receipt/[workOrderId]/page.tsx
│   ├── components/
│   │   ├── dashboard/
│   │   ├── reviews/
│   │   ├── hearing/
│   │   ├── receipt/
│   │   ├── scorecards/
│   │   ├── planner/
│   │   └── map/
│   ├── lib/
│   │   ├── api.ts
│   │   ├── query-client.ts
│   │   └── types.ts
│   └── public/
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── data/
│   ├── cache/
│   │   └── claude_responses.json
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── api/
│   │   │   ├── summary.py
│   │   │   ├── reviews.py
│   │   │   ├── scorecards.py
│   │   │   ├── planner.py
│   │   │   └── receipts.py
│   │   ├── services/
│   │   │   ├── audit_adapter.py
│   │   │   ├── scorecard_adapter.py
│   │   │   ├── budget_adapter.py
│   │   │   ├── claude_service.py
│   │   │   ├── hearing_service.py
│   │   │   └── receipt_service.py
│   │   └── templates/
│   │       └── hearing_fallback.py
│   └── tests/
│       ├── test_audit.py
│       ├── test_verdicts.py
│       └── test_api.py
└── docs/
    ├── architecture.md
    └── demo-script.md
```

If Kshitij's existing modules use different names or paths, inspect them first and adapt the API wrapper around them. Do not rewrite working pandas calculations merely to match this example structure.

---

## 6. Core Data Sources

Use the supplied synthetic dataset:

- `complaints.csv`
- `work_orders.csv`
- `rate_card.csv`
- `roads.csv` and `roads.geojson`
- `contractors.csv`
- `wards.csv` and `wards.geojson`
- `traffic.csv`
- `accidents.csv`
- `flood_hotspots.csv`
- `rainfall_daily.csv`
- `tides.csv`
- `facilities.csv`
- `localities.csv`
- `social_posts.csv` only when evidence can be linked responsibly

Every UI claim must carry its source record ID or the calculation that produced it.

---

## 7. Audit Rules

All financial and scoring calculations must be deterministic. Claude explains results; Claude does not calculate them.

### 7.1 Expected cost

```python
if rate_card.unit == "per sqm":
    expected_cost = work_order.area_sqm * rate_card.standard_rate_inr
else:
    expected_cost = rate_card.standard_rate_inr

rate_ratio = work_order.cost_inr / expected_cost
```

### 7.2 Rate-card classification

```text
Below 0.75×: Low-cost/data-quality outlier; do not call overbilling
0.75×–1.30×: Normal range
Above 1.30×–1.40×: Context band; show but do not count as a primary anomaly
Above 1.40×: Rate-card review lead
```

The UI must show the expected amount, actual amount, ratio and threshold. Do not silently change the threshold.

### 7.3 Duplicate-like work-order rule

Use Kshitij's existing duplicate logic if it has already been validated. At minimum, a strong duplicate candidate should consider:

```python
duplicate_candidate = (
    missing_linked_complaint
    and same_road
    and same_work_type
    and same_repair_method
    and same_or_nearly_same_area
    and days_apart <= 4
    and cost_difference_pct <= 6
)
```

Show the two orders side by side. Call them **duplicate-like records** or a **possible duplicate charge**, never confirmed fraud.

### 7.4 DLP/warranty rule

```python
dlp_review = road.under_dlp == "Y" and work_order.cost_inr > 0
```

The dataset does not identify the original DLP contractor. Therefore:

- Do not blame the contractor on the new work order automatically.
- Do not claim the named contractor is the original warranty holder.
- Route the case to the **Ward Warranty Desk** to retrieve the original contract and determine liability.
- Count this primarily as a ward/system control issue until ownership is established.

### 7.5 Deduplicated counting

A work order caught by two or more rules must count as one review lead with multiple reasons:

```json
{
  "work_order_id": "WO25-02469",
  "rules": ["POSSIBLE_DUPLICATE", "DLP_REVIEW"],
  "lead_count": 1
}
```

Never add rule counts together and present the sum as unique suspicious work orders.

---

## 8. Fair Accountability

### 8.1 Contractor comparisons

Compare contractors only within fair peer groups:

- Same repair method
- Same SLA tier
- Preferably the same work type and road class
- Show sample size
- Show the comparison group
- Show confidence or a low-sample warning

Contractor score dimensions:

1. SLA reliability
2. Durability/reopen rate
3. Rate-card alignment
4. Evidence completeness

Do not assign DLP leakage to the current contractor unless the original warranty owner is known.

### 8.2 Ward scorecards

Ward score dimensions:

1. Complaint-to-work-order linkage completeness
2. DLP/warranty control
3. Duplicate-payment control
4. SLA oversight
5. Risk-adjusted budget allocation

The scorecard must separate:

- Contractor delivery problems
- Ward/system process problems
- Missing or poor-quality data

### 8.3 Language

Allowed:

- Review lead
- Possible duplicate
- Record conflict
- Requires supporting evidence
- Warranty ownership not established
- Higher/lower than comparable jobs

Forbidden:

- Fraud
- Corrupt
- Scam
- Guilty
- Stole
- Legal violation, unless independently proven by supplied data

---

## 9. Three-Way Verdict

Every review lead must end in one actionable recommendation.

### Release Payment

Use when:

- No material audit rule remains unresolved, or
- Supporting evidence adequately explains the review lead.

### Hold for Evidence

Use when:

- A rate-card review lead exists.
- A duplicate-like record exists.
- Required supporting documentation is missing.
- Two records conflict and the dataset cannot resolve the conflict.

Display the exact evidence required, such as:

- Geotagged before/after photographs
- Measurement book entry
- Engineer completion certificate
- Separate-defect justification
- Emergency-work approval
- Itemised rate deviation approval

### Warranty Review

User-facing button may read **Return Under Warranty**, but the explanatory subtitle must be:

> Route to Ward Warranty Desk to identify the original DLP owner and verify whether BMC should pay.

Use when:

- The road is under DLP and a paid work order exists.

Verdict precedence for the initial recommendation:

```text
DLP review → Warranty Review
Else duplicate or rate anomaly → Hold for Evidence
Else → Release Payment
```

The officer must be able to override the recommendation, but an override requires a short written reason stored in SQLite.

---

## 10. Claude Fair Hearing

The Fair Hearing is the signature interaction. It must show fairness happening on screen.

### Inputs

Send Claude only structured evidence:

- Work-order facts
- Linked complaint facts and translated text
- Rate-card calculation produced by Python
- Duplicate comparison produced by Python
- DLP status
- SLA and reopen status
- Relevant rainfall, flood and traffic context
- Data limitations
- Source record IDs

### Output schema

Claude must return valid JSON matching this structure:

```json
{
  "auditor_case": {
    "summary": "",
    "evidence": [],
    "source_ids": []
  },
  "fairness_case": {
    "possible_legitimate_context": [],
    "limitations": [],
    "source_ids": []
  },
  "recommended_verdict": "RELEASE_PAYMENT | HOLD_FOR_EVIDENCE | WARRANTY_REVIEW",
  "reasoning": "",
  "evidence_required": [],
  "citizen_explanation": "",
  "officer_brief": "",
  "confidence": "HIGH | MEDIUM | LOW"
}
```

### System prompt

```text
You are the fairness layer in a civic road-repair payment review system.

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
claim. If evidence is insufficient, say so explicitly.
```

### Cache and fallback

- Cache responses by a stable hash of the structured evidence.
- Commit `backend/cache/claude_responses.json` with responses for the golden demo cases.
- If the API key is missing, API call fails or JSON validation fails, use the cache.
- If there is no cached response, use a deterministic template assembled from the audit rules.
- The UI must never become unusable because Claude is unavailable.

---

## 11. Public Repair Receipt

Route:

```text
/receipt/[workOrderId]
```

The receipt must show:

- Complaint summary in the selected language
- Work-order ID
- Road and ward
- Contractor named on the work order
- Repair method
- Completed date
- Amount billed
- SLA result
- Reopened-within-30-days result
- DLP status
- Current verdict/status
- Evidence completeness
- Source record IDs
- “Did this repair survive?” interaction

### Citizen durability feedback

Buttons:

- **Yes, it is holding up**
- **No, the problem returned**
- **Not sure**

If the user selects **No**:

1. Ask for a short description.
2. Allow a placeholder/demo photo reference; do not claim real image verification if none exists.
3. Store feedback in SQLite.
4. If the road is under DLP, create a `WARRANTY_REVIEW` feedback case.
5. If DLP ownership is unknown, route it to the Ward Warranty Desk.
6. Do not automatically accuse or charge the current contractor.

For the hackathon, the QR code can point to the local receipt URL. This is a demonstrated future workflow; do not imply that physical QR codes already exist across Mumbai.

---

## 12. Recover, Then Reinvest

The planner must accept:

- Ward
- Available budget
- Optional held/recovered amount

It must return a budget-capped list of recommended interventions. It cannot recommend spending more than the supplied budget.

Prioritisation inputs:

- Road-condition accidents and severity
- Traffic and congestion
- BEST bus exposure
- Flood-hotspot proximity
- Rainfall and tide exposure
- Nearby hospitals and schools
- Repeat complaints and repair failures
- Repair-method durability
- Lifetime cost, not only cheapest upfront price

Warranty roads must first be routed to warranty review at an assumed **₹0 new BMC repair allocation**, subject to identifying the original DLP owner. Do not count a zero-cost warranty action as a confirmed saving until ownership is established.

Every recommendation must explain:

- Why this road is prioritised
- Recommended repair method
- Estimated cost
- Relevant risk evidence
- Historical durability of the method
- Amount remaining after selection

---

## 13. Required Screens

### Screen A — City Overview

Show:

- Unique review leads
- Amount requiring review
- Complaint-to-work-order linkage rate
- DLP review count
- Ward accountability summary
- Contractor accountability summary
- Sankey: complaints → issues → work orders → verdicts
- Map of review leads and priority roads

The overview is context, not the main demo.

### Screen B — Review Inbox

Table columns:

- Work-order ID
- Ward
- Road
- Contractor
- Amount
- Rules triggered
- Confidence
- Recommended verdict
- Open Case button

Filters:

- Ward
- Contractor
- Repair method
- Rate-card lead
- Duplicate-like record
- DLP review
- Verdict

### Screen C — Case Detail and Fair Hearing

This is the main demo screen.

Layout:

1. Complaint-to-payment evidence timeline
2. Actual-versus-expected cost card
3. Duplicate comparison, when present
4. DLP and road-context card
5. Auditor case
6. Fairness Advocate case
7. Three-way verdict
8. Evidence request checklist
9. Save/override decision
10. Open Public Receipt

### Screen D — Scorecards

Tabs:

- Contractors
- Wards

Show component scores, peer group, sample size and evidence links. Avoid a leaderboard that hides context.

### Screen E — Next-Rupee Planner

Show:

- Ward selector
- Budget input
- Selected interventions
- Remaining amount
- Risk and lifetime-cost explanation
- Map of selected roads

### Screen F — Public Repair Receipt

Mobile-first, simple language, multilingual selector, durability feedback and clear status.

---

## 14. Golden Demo Case

Use this case for the polished end-to-end demonstration:

### Sion Trombay Road — RD0235

Relevant records:

- `BMC25-003870`: English complaint reporting a tyre burst caused by a pothole; 37 upvotes.
- `BMC25-003869`: Marathi complaint reporting an open drain cover; categorised as a pothole and closed as duplicate.
- `WO25-01483`: Mastic asphalt, 3.4 sqm, ₹17,181, completed 9 August 2025.
- `WO25-02469`: No complaint, same road, contractor, method and area, ₹16,754, recorded the next day.
- `RD0235`: Under DLP, arterial, BEST bus route.
- Traffic context: 3,723 peak-hour vehicles, congestion 8.3/10, 15 bus routes, 53% two-wheeler share.
- Accident data contains multiple road-condition-related incidents.

Do not claim that a specific repair caused an accident. The correct wording is:

> A later road-condition signal conflicts with the completion record and supports physical verification; it does not prove causation.

Expected initial verdict:

```text
WARRANTY REVIEW

Route to the Ward Warranty Desk to identify the original DLP owner. Also
request geotagged before/after photographs, the measurement book entry and an
explanation of why the second record represents separate work.
```

The case should visibly demonstrate:

- Multilingual complaint understanding
- Category/linkage inconsistency
- Duplicate-like work-order evidence
- DLP process control
- Auditor and Fairness Advocate
- Three-way verdict
- Public Repair Receipt
- Citizen durability feedback
- Budget reinvestment

---

## 15. Backend API Contract

Use `/api` as the prefix.

### Health

```text
GET /api/health
```

```json
{
  "status": "ok",
  "data_loaded": true,
  "claude_mode": "live | cache | template"
}
```

### Overview

```text
GET /api/summary
```

Return aggregate cards, Sankey nodes/links, map points and methodology notes.

### Review inbox

```text
GET /api/reviews
GET /api/reviews/{work_order_id}
```

Support query parameters for ward, contractor, rule, verdict, repair method, limit and offset.

### Fair hearing

```text
POST /api/reviews/{work_order_id}/hearing
```

Return the validated Fair Hearing JSON plus `mode: live | cache | template`.

### Save verdict

```text
PATCH /api/reviews/{work_order_id}/verdict
```

Request:

```json
{
  "verdict": "RELEASE_PAYMENT | HOLD_FOR_EVIDENCE | WARRANTY_REVIEW",
  "officer_reason": "Required for an override or confirmation note"
}
```

### Scorecards

```text
GET /api/scorecards/contractors
GET /api/scorecards/contractors/{contractor_id}
GET /api/scorecards/wards
GET /api/scorecards/wards/{ward_code}
```

### Planner

```text
GET /api/planner/recommendations?ward_code=M%2FE&budget_inr=100000
```

### Receipt

```text
GET /api/receipts/{work_order_id}?language=en
POST /api/receipts/{work_order_id}/durability-feedback
```

Feedback request:

```json
{
  "answer": "SURVIVED | FAILED | UNSURE",
  "description": "",
  "language": "en"
}
```

---

## 16. Minimum Shared TypeScript Types

```typescript
export type Verdict =
  | "RELEASE_PAYMENT"
  | "HOLD_FOR_EVIDENCE"
  | "WARRANTY_REVIEW";

export type ReviewRule =
  | "RATE_CARD_REVIEW"
  | "POSSIBLE_DUPLICATE"
  | "DLP_REVIEW"
  | "LOW_COST_DATA_QUALITY";

export interface ReviewLead {
  workOrderId: string;
  wardCode: string;
  roadId: string;
  roadName: string;
  contractorId: string;
  contractorName: string;
  amountInr: number;
  expectedAmountInr: number;
  rateRatio: number;
  rules: ReviewRule[];
  recommendedVerdict: Verdict;
  confidence: "HIGH" | "MEDIUM" | "LOW";
}
```

The backend remains the source of truth. The frontend must not recalculate audit results.

---

## 17. Frontend Requirements

- Use TanStack Query for every backend request.
- Provide loading, empty and error states.
- Use Indian currency formatting.
- Use accessible colour plus text/icon labels; never rely on red/green alone.
- Use responsive layouts; the Public Repair Receipt must be mobile-first.
- Dynamically import Leaflet components with SSR disabled.
- Load Leaflet CSS explicitly.
- Keep the primary navigation short: Overview, Reviews, Scorecards, Planner.
- Do not expose the Anthropic API key or call Anthropic from the browser.

Suggested verdict colours:

- Release: green
- Hold: amber
- Warranty Review: blue or purple, not accusatory red

---

## 18. SQLite Models

At minimum, persist:

### OfficerDecision

- `id`
- `work_order_id`
- `recommended_verdict`
- `final_verdict`
- `officer_reason`
- `created_at`

### DurabilityFeedback

- `id`
- `work_order_id`
- `answer`
- `description`
- `language`
- `created_at`
- `generated_warranty_review`

### HearingCacheMetadata

- `id`
- `work_order_id`
- `evidence_hash`
- `mode`
- `created_at`

Do not commit the generated SQLite database file.

---

## 19. Public Repository Security

Create a root `.gitignore` containing at least:

```gitignore
# Secrets
.env
.env.*
!.env.example
!.env.local.example

# Frontend
node_modules/
.next/
out/

# Python
.venv/
venv/
__pycache__/
*.py[cod]
.pytest_cache/

# Database
*.db
*.sqlite
*.sqlite3

# OS/editor
.DS_Store
.idea/
.vscode/
```

Backend `.env.example`:

```dotenv
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=
FRONTEND_ORIGIN=http://localhost:3000
```

Frontend `.env.local.example`:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
```

Never commit a real key. If a key is accidentally pushed, revoke it immediately; deleting it in a later commit is insufficient because it remains in Git history.

---

## 20. Local Run Instructions Required in README

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open:

```text
Frontend: http://localhost:3000
Backend docs: http://localhost:8000/docs
```

Configure FastAPI CORS for `http://localhost:3000`.

---

## 21. Implementation Priority

Build in this order:

### Priority 1 — Must work

1. Load datasets and existing pandas modules.
2. Produce deduplicated review leads.
3. Review Inbox.
4. Golden-case detail page.
5. Three-way deterministic verdict.
6. Cached/template Fair Hearing.

### Priority 2 — Winning differentiation

7. Live Claude Fair Hearing.
8. Contractor and ward scorecards.
9. Public Repair Receipt.
10. Citizen durability feedback.

### Priority 3 — Complete story

11. Budget-capped Next-Rupee Planner.
12. Overview Sankey.
13. Leaflet map.
14. Additional multilingual citizen questions.

If time becomes limited, preserve the complete golden-case journey instead of creating unfinished pages.

---

## 22. Acceptance Criteria

The build is complete only when all of the following are true:

- [ ] A judge can start both applications using the README.
- [ ] The repository contains no secret key or SQLite database.
- [ ] The frontend never calls Anthropic directly.
- [ ] Audit calculations come from Python, not Claude.
- [ ] A work order caught by multiple rules counts once.
- [ ] Rate-card thresholds are visible and match this specification.
- [ ] Contractor comparisons state their peer group and sample size.
- [ ] DLP cases do not automatically blame the current contractor.
- [ ] Every review lead ends with one of three verdicts.
- [ ] Officer overrides require a written reason.
- [ ] The Fair Hearing presents both audit evidence and legitimate context.
- [ ] Claude responses include source IDs and survive API failure through cache/template fallback.
- [ ] The Sion Trombay case works end to end.
- [ ] The Public Repair Receipt works on a mobile-sized screen.
- [ ] “Problem returned” creates a warranty-review feedback case.
- [ ] Planner recommendations never exceed the supplied budget.
- [ ] All financial exposure is labelled as requiring review, not confirmed loss.

---

## 23. Two-Minute Demo Path

1. Open the Overview for five seconds and state that NagarLens connects the full money trail.
2. Open the Review Inbox and select `WO25-02469`.
3. Show the multilingual complaints and matching prior work order.
4. Show the rate/DLP/duplicate evidence and source IDs.
5. Run the Claude Fair Hearing.
6. Show Auditor versus Fairness Advocate.
7. Accept the `Warranty Review` verdict and evidence checklist.
8. Open the Public Repair Receipt.
9. Select “No, the problem returned” and show the warranty case created.
10. Open the planner and show how available money is directed to higher-risk work.

Closing line:

> **NagarLens does not merely find anomalies. It turns evidence into a fair decision, lets citizens verify whether repairs survive, and makes the next rupee defensible.**

---

## 24. Non-Negotiable Product Principles

1. **Evidence before accusation**
2. **Deterministic calculations before AI explanation**
3. **Fair peer comparisons before rankings**
4. **System failures separated from contractor failures**
5. **Every flag leads to an action**
6. **Every action remains traceable to source records**
7. **The demo works even without an Anthropic API key**

