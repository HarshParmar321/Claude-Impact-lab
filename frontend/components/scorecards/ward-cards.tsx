import Link from "next/link";
import type { ScorecardMethodology, WardScore } from "@/lib/types";
import { camelLabel, inr, num, pct } from "@/lib/format";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SourceId } from "@/components/layout/badges";
import { cn } from "@/lib/utils";

function Bar({ label, value, title }: { label: string; value: number | null; title: string }) {
  return (
    <div title={title}>
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="tabular-nums font-medium">{pct(value)}</span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-primary/70" style={{ width: `${value ?? 0}%` }} />
      </div>
    </div>
  );
}

export function WardCards({ items, methodology, highlight }: { items: WardScore[]; methodology: ScorecardMethodology; highlight?: string }) {
  return (
    <div className="space-y-3">
      <div className="rounded-lg border bg-muted/40 p-3 text-xs text-muted-foreground">
        Wards listed in code order. Each score separates contractor delivery, ward/system process and data-quality problems. Hover a bar for its definition.
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {items.map((w) => (
          <Card key={w.wardCode} id={`ward-${w.wardCode}`} className={cn(highlight === w.wardCode && "ring-2 ring-primary")}>
            <CardHeader>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <CardTitle className="text-base">{w.wardName}</CardTitle>
                  <CardDescription>{w.zone} · {num(w.metrics.workOrders)} work orders · {inr(w.metrics.billedAmountInr)} billed</CardDescription>
                </div>
                <div className="text-right">
                  <div className="text-xl font-semibold tabular-nums">{w.overallScore}</div>
                  <div className="text-[11px] text-muted-foreground">composite</div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                {(Object.keys(w.dimensions) as (keyof WardScore["dimensions"])[]).map((k) => (
                  <Bar key={k} label={camelLabel(k)} value={w.dimensions[k]} title={methodology.wardDimensions[k] ?? ""} />
                ))}
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="rounded-lg border p-2">
                  <div className="mb-1 font-medium">Contractor delivery</div>
                  <div>{w.attribution.contractorDelivery.slaBreaches} SLA breaches</div>
                  <div>{w.attribution.contractorDelivery.reopenedWithin30d} reopened</div>
                  <div>{w.attribution.contractorDelivery.evidenceGaps} evidence gaps</div>
                </div>
                <div className="rounded-lg border border-warranty/30 bg-warranty-bg/50 p-2">
                  <div className="mb-1 font-medium">Ward / system</div>
                  <div>{w.attribution.wardSystem.workOrdersWithoutComplaint} no complaint link</div>
                  <div>{w.attribution.wardSystem.dlpRoadPayments} DLP-road payments</div>
                  <div>{w.attribution.wardSystem.duplicateLikeRecords} duplicate-like</div>
                </div>
                <div className="rounded-lg border border-dashed p-2">
                  <div className="mb-1 font-medium">Data quality</div>
                  <div>{w.attribution.dataQuality.lowCostOutliers} low-cost outliers</div>
                  <div>{w.attribution.dataQuality.complaintCategoryConflicts} category conflicts</div>
                </div>
              </div>
              <div className="space-y-1 text-xs">
                <div className="text-muted-foreground">Evidence (sample records)</div>
                <div className="flex flex-wrap gap-1">
                  {[...w.evidenceLinks.dlpRoadPayments.slice(0, 3), ...w.evidenceLinks.duplicateLike.slice(0, 3)].map((i) => (
                    <Link key={i} href={`/reviews/${i}`}><SourceId id={i} className="hover:text-primary" /></Link>
                  ))}
                  {w.evidenceLinks.categoryConflicts.slice(0, 2).map((i) => <SourceId key={i} id={i} />)}
                </div>
                <Link className="text-primary hover:underline" href={`/reviews?ward=${encodeURIComponent(w.wardCode)}`}>
                  {w.metrics.uniqueReviewLeads} review leads in this ward →
                </Link>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
