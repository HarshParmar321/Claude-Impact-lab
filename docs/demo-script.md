# Two-minute demo script

**Setup:** backend on :8000, frontend on :3000. No API key needed (header shows *Claude: cached*). For a clean run, delete `backend/nagarlens.db` before starting.

| Time | Screen | Do | Say |
|---|---|---|---|
| 0:00 | Overview | Pause 5 s on the cards and Sankey | "NagarLens connects the full money trail: complaints → issues → work orders → verdicts. 282 unique review leads, each counted once." |
| 0:10 | Reviews | Click **Open case** on the pinned WO25-02469 | "One inbox, deduplicated. This order triggers two rules but counts as one lead." |
| 0:20 | Case | Scroll the record conflicts and complaints | "A Marathi complaint about an open drain cover was filed as a pothole and closed as a duplicate of an English complaint filed 22 minutes *later*." |
| 0:35 | Case | Point at the cost card and the duplicate table | "The price is normal, 1.07×. The problem is different: the same 3.4 sqm mastic patch, same contractor, a day apart, no complaint, on a road still under DLP." |
| 0:50 | Case | **Run Fair Hearing** | "Claude hears both sides. The Auditor sets out the evidence. The Fairness Advocate gives the legitimate context: a second defect is possible, heavy rain, 3,723 peak-hour vehicles, and the contractor isn't shown to be the warranty holder." |
| 1:10 | Case | Select **Return Under Warranty**, type a note, **Confirm decision** | "One action: route to the Ward Warranty Desk, and request the geotagged photos, the measurement book entry and a separate-work justification. Overrides need a written reason." |
| 1:25 | Receipt | **Open Public Receipt**, switch to मराठी | "The citizen sees the same facts in plain language, in their language." |
| 1:35 | Receipt | Tap **No, the problem returned** → describe → send | "A failed repair goes straight back to warranty review. Nobody is auto-blamed." |
| 1:45 | Planner | M/E, ₹1,00,000 | "Sion Trombay Road goes to warranty first at ₹0 new BMC money. The budget funds the next-riskiest roads with the method that's cheapest over its lifetime, not the cheapest today." |

**Closing line:** NagarLens does not merely find anomalies. It turns evidence into a fair decision, lets citizens verify whether repairs survive, and makes the next rupee defensible.

**Fallback talking points**
- *No internet for map tiles:* markers still render on a grey background; the data is local.
- *Asked "is this fraud?":* "It's a review lead. The records conflict and need verification. NagarLens never makes that call."
- *Asked about the data:* the dataset is synthetic; swap in the official CSVs with the same names and re-run the cache builder.
