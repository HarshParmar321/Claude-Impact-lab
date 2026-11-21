import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { inr, ratio } from "@/lib/format";
import type { CaseDetail } from "@/lib/types";
import { SourceId } from "@/components/layout/badges";
import { cn } from "@/lib/utils";

const MAX = 2.2;
const BANDS = [
  { from: 0, to: 0.75, cls: "bg-muted", label: "<0.75 data quality" },
  { from: 0.75, to: 1.3, cls: "bg-release-bg", label: "0.75–1.30 normal" },
  { from: 1.3, to: 1.4, cls: "bg-hold-bg", label: "1.30–1.40 context" },
  { from: 1.4, to: MAX, cls: "bg-warranty-bg", label: ">1.40 review lead" },
];

export function CostCard({ rate }: { rate: CaseDetail["rateCheck"] }) {
  const pos = rate.rateRatio === null ? null : Math.min(rate.rateRatio, MAX) / MAX;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Actual vs expected cost</CardTitle>
        <CardDescription>
          Rate card <SourceId id={rate.rateCardId} /> · {inr(rate.standardRateInr)} {rate.unit}
          {rate.unit === "per sqm" && <> × {rate.areaSqm} sqm</>}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <dl className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded-lg bg-muted/60 p-2">
            <dt className="text-xs text-muted-foreground">Expected</dt>
            <dd className="font-semibold tabular-nums">{inr(rate.expectedCostInr)}</dd>
          </div>
          <div className="rounded-lg bg-muted/60 p-2">
            <dt className="text-xs text-muted-foreground">Actual billed</dt>
            <dd className="font-semibold tabular-nums">{inr(rate.actualCostInr)}</dd>
          </div>
          <div className="rounded-lg bg-muted/60 p-2">
            <dt className="text-xs text-muted-foreground">Ratio</dt>
            <dd className="font-semibold tabular-nums">{ratio(rate.rateRatio)}</dd>
          </div>
        </dl>
        {pos !== null && (
          <div>
            <div className="relative flex h-3 overflow-hidden rounded-full border" aria-hidden>
              {BANDS.map((b) => (
                <div key={b.label} className={cn(b.cls, "h-full border-r last:border-r-0")} style={{ width: `${((b.to - b.from) / MAX) * 100}%` }} />
              ))}
            </div>
            <div className="relative h-5">
              <div className="absolute -top-4 h-5 w-0.5 bg-foreground" style={{ left: `calc(${pos * 100}% - 1px)` }} />
              <div className="absolute top-1 -translate-x-1/2 text-[11px] font-medium" style={{ left: `${pos * 100}%` }}>{ratio(rate.rateRatio)}</div>
            </div>
            <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px] text-muted-foreground sm:grid-cols-4">
              {rate.thresholds.map((t) => (
                <span key={t.band} className={cn(t.band === rate.rateBand && "font-semibold text-foreground")}>
                  {t.label}: {t.meaning}
                </span>
              ))}
            </div>
          </div>
        )}
        <p className="text-sm">
          <span className="font-medium">Band:</span> {rate.bandMeaning}
        </p>
        <p className="font-mono text-[11px] text-muted-foreground">{rate.formula}</p>
      </CardContent>
    </Card>
  );
}
