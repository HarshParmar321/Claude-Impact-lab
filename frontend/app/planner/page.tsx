"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Info, ShieldQuestion, TrendingDown } from "lucide-react";
import { api } from "@/lib/api";
import { camelLabel, humanize, inr, num } from "@/lib/format";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { StatCard } from "@/components/dashboard/stat-card";
import { RoadMap, type MapPoint } from "@/components/map/road-map";
import { SourceId } from "@/components/layout/badges";
import { EmptyState, ErrorState, LoadingBlock, PageHeader } from "@/components/layout/states";

function useDebounced<T>(v: T, ms = 400) {
  const [d, setD] = useState(v);
  useEffect(() => {
    const t = setTimeout(() => setD(v), ms);
    return () => clearTimeout(t);
  }, [v, ms]);
  return d;
}

export default function PlannerPage() {
  const [ward, setWard] = useState("M/E");
  const [budget, setBudget] = useState("100000");
  const [recovered, setRecovered] = useState("0");
  const b = useDebounced(Math.max(0, Number(budget) || 0));
  const rv = useDebounced(Math.max(0, Number(recovered) || 0));
  const wards = useQuery({ queryKey: ["planner-wards"], queryFn: api.plannerWards });
  const plan = useQuery({ queryKey: ["plan", ward, b, rv], queryFn: () => api.planner(ward, b, rv), placeholderData: keepPreviousData });
  const p = plan.data;

  const points: MapPoint[] = p
    ? [
        ...p.selected.map((s, i) => ({ id: s.roadId, lat: s.lat, lon: s.lon, kind: "selected" as const, title: `#${i + 1} ${s.roadName}`,
          lines: [`${inr(s.estimatedCostInr)} · ${humanize(s.recommendedMethod)}`, `Priority ${s.priorityScore}/100`], weight: 3 })),
        ...p.notSelected.map((s) => ({ id: s.roadId, lat: s.lat, lon: s.lon, kind: "priority" as const, title: s.roadName,
          lines: [s.reasonNotSelected ?? ""], weight: 1 })),
      ]
    : [];

  return (
    <div className="space-y-5">
      <PageHeader
        title="Next-Rupee Planner"
        description="Recover, then reinvest. Roads are ranked by public risk; warranty roads go to the Ward Warranty Desk first; the remaining budget buys the method with the lowest lifetime cost. The plan never exceeds the money entered."
      />

      <Card>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <div className="space-y-1.5">
            <Label htmlFor="ward">Ward</Label>
            <NativeSelect id="ward" className="w-full" value={ward} onChange={(e) => setWard(e.target.value)}>
              {wards.data?.items.map((w) => <option key={w.wardCode} value={w.wardCode}>{w.wardName}</option>) ?? <option value="M/E">M/E</option>}
            </NativeSelect>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="budget">Available budget (₹)</Label>
            <Input id="budget" inputMode="numeric" value={budget} onChange={(e) => setBudget(e.target.value.replace(/[^0-9]/g, ""))} />
            <div className="text-xs text-muted-foreground">{inr(b)}</div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="recovered">Recovered amount (₹, optional)</Label>
            <Input id="recovered" inputMode="numeric" value={recovered} onChange={(e) => setRecovered(e.target.value.replace(/[^0-9]/g, ""))} />
            <div className="text-xs text-muted-foreground">Only money actually recovered or released back</div>
          </div>
        </CardContent>
      </Card>

      {plan.isLoading ? <LoadingBlock rows={4} /> : plan.error || !p ? <ErrorState error={plan.error} onRetry={() => plan.refetch()} /> : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard label="Spendable" value={inr(p.spendableInr)} hint={`Budget ${inr(p.budgetInr)} + recovered ${inr(p.recoveredInr)}`} />
            <StatCard label="Allocated" value={inr(p.allocatedInr)} hint={`${p.selected.length} intervention(s)`} />
            <StatCard label="Remaining" value={inr(p.remainingInr)} hint="Never negative: plan is budget-capped" />
            <StatCard label="Held for review in ward" value={inr(p.heldForReviewInWardInr)} hint="Not spendable until resolved" />
          </div>

          <div className="grid gap-5 lg:grid-cols-5">
            <div className="space-y-4 lg:col-span-3">
              {p.warrantyRoutes.length > 0 && (
                <Alert variant="warranty">
                  <ShieldQuestion />
                  <AlertTitle>Warranty routes first: ₹0 new BMC allocation (assumed)</AlertTitle>
                  <AlertDescription>
                    <ul className="w-full space-y-1">
                      {p.warrantyRoutes.map((w) => (
                        <li key={w.roadId} className="flex flex-wrap items-center justify-between gap-2">
                          <span><SourceId id={w.roadId} /> {w.roadName} · priority {w.priorityScore}</span>
                          <Link className="text-xs underline" href={`/reviews?ward=${encodeURIComponent(p.wardCode)}&rule=DLP_REVIEW`}>DLP leads</Link>
                        </li>
                      ))}
                    </ul>
                    <p className="text-xs">{p.warrantyRoutes[0].note}</p>
                  </AlertDescription>
                </Alert>
              )}
              <Card>
                <CardHeader>
                  <CardTitle>Selected interventions</CardTitle>
                  <CardDescription>In priority order, with the amount left after each selection</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {p.selected.length === 0 && <EmptyState title="Nothing fits this budget" detail="Increase the budget to fund the highest-priority non-warranty road." />}
                  {p.selected.map((s, i) => (
                    <div key={s.roadId} className="rounded-xl border p-4">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <div className="font-semibold">#{i + 1} {s.roadName}</div>
                          <div className="text-xs text-muted-foreground"><SourceId id={s.roadId} /> · {humanize(s.roadClass)} · priority {s.priorityScore}/100 · {s.estimatedAreaSqm} sqm estimated distress</div>
                        </div>
                        <div className="text-right">
                          <div className="font-semibold tabular-nums">{inr(s.estimatedCostInr)}</div>
                          <div className="text-xs text-muted-foreground">Remaining after: {inr(s.remainingAfterInr ?? 0)}</div>
                        </div>
                      </div>
                      <div className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
                        <div>
                          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Why prioritised</div>
                          <ul className="mt-1 list-disc pl-5">{s.whyPrioritised.map((w) => <li key={w}>{w}</li>)}</ul>
                        </div>
                        <div>
                          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Recommended method</div>
                          <p className="mt-1">
                            {humanize(s.recommendedMethod)} (<SourceId id={s.rateCardId} />): {s.methodDurability.reopenRatePct}% historical 30-day reopen rate across {num(s.methodDurability.historicalJobs)} jobs; {s.methodDurability.effectiveLifeMonths} months effective life.
                          </p>
                          <p className="mt-1 flex items-start gap-1 text-xs text-muted-foreground">
                            <TrendingDown className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                            3-year cost {inr(s.lifetimeCost3yInr)} vs {inr(s.cheapestLifetimeCost3yInr)} for {humanize(s.cheapestUpfrontMethod)} (cheapest upfront at {inr(s.cheapestUpfrontCostInr)})
                          </p>
                        </div>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-1 text-[11px] text-muted-foreground">
                        Risk score parts:
                        {Object.entries(s.riskEvidence).filter(([k, v]) => typeof v === "number" && k in p.weights).map(([k, v]) => (
                          <span key={k} className="rounded bg-muted px-1.5 py-0.5">{camelLabel(k)} {Number(v).toFixed(1)}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>

            </div>

            <div className="space-y-4 lg:col-span-2">
              <Card>
                <CardHeader><CardTitle>Selected roads</CardTitle></CardHeader>
                <CardContent><RoadMap points={points} height={320} /></CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Lifetime cost by method</CardTitle>
                  <CardDescription>Pothole patching · from rate card and work-order history</CardDescription>
                </CardHeader>
                <CardContent>
                  <table className="w-full text-xs">
                    <thead className="text-left text-muted-foreground">
                      <tr><th className="py-1 font-medium">Method</th><th className="font-medium">Rate/sqm</th><th className="font-medium">Reopen</th><th className="font-medium">Eff. life</th><th className="font-medium">₹/sqm-year</th></tr>
                    </thead>
                    <tbody>
                      {p.methodComparison.map((m, i) => (
                        <tr key={m.repairMethod} className={i === 0 ? "border-t font-semibold" : "border-t"}>
                          <td className="py-1.5">{humanize(m.repairMethod)}</td>
                          <td className="tabular-nums">{inr(m.standardRateInr)}</td>
                          <td className="tabular-nums">{(m.reopenRate * 100).toFixed(1)}%</td>
                          <td className="tabular-nums">{m.effectiveLifeMonths} mo</td>
                          <td className="tabular-nums">{inr(m.lifetimeCostPerSqmYear)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
              <Card className="bg-muted/40">
                <CardContent className="space-y-2 text-xs text-muted-foreground">
                  <div className="flex items-center gap-1 font-medium text-foreground"><Info className="size-3.5" />Methodology</div>
                  <p>{p.methodology}</p>
                  <p>Weights: {Object.entries(p.weights).map(([k, v]) => `${camelLabel(k)} ${v}`).join(" · ")}</p>
                  <p>{p.heldNote}</p>
                </CardContent>
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
