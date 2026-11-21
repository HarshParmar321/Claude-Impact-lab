import { Bus, CloudRain, Hospital, ShieldQuestion, Waves } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { fmtDate, humanize, num } from "@/lib/format";
import type { CaseDetail } from "@/lib/types";
import { SourceId } from "@/components/layout/badges";

export function DlpContextCard({ dlp, ctx }: { dlp: CaseDetail["dlp"]; ctx: CaseDetail["context"] }) {
  const heavy = ctx.rainfall.filter((r) => r.rainfallMm >= 60);
  const rcAccidents = ctx.accidents.filter((a) => a.roadConditionRelated);
  return (
    <Card>
      <CardHeader>
        <CardTitle>DLP and road context</CardTitle>
        <CardDescription>
          <SourceId id={ctx.road.roadId} /> · {humanize(ctx.road.roadClass)} · priority score {ctx.priorityScore}/100
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {dlp.underDlp ? (
          <Alert variant="warranty">
            <ShieldQuestion />
            <AlertTitle>Under Defect Liability Period until {fmtDate(dlp.dlpEndDate)}</AlertTitle>
            <AlertDescription>
              <p>{dlp.note}</p>
              <p className="font-medium">Warranty owner known: {dlp.warrantyOwnerKnown ? "Yes" : "No — not in the dataset"}</p>
            </AlertDescription>
          </Alert>
        ) : (
          <p className="text-muted-foreground">{dlp.note}</p>
        )}
        <dl className="grid grid-cols-2 gap-3">
          <div>
            <dt className="flex items-center gap-1 text-xs text-muted-foreground"><Bus className="size-3.5" aria-hidden />Traffic</dt>
            <dd className="tabular-nums">{num(ctx.traffic.peakHourVehicles)} peak-hour vehicles · congestion {ctx.traffic.congestionIndex}/10</dd>
            <dd className="text-xs text-muted-foreground">{ctx.traffic.busRoutes} BEST routes · {Math.round(ctx.traffic.twoWheelerShare * 100)}% two-wheelers</dd>
          </div>
          <div>
            <dt className="flex items-center gap-1 text-xs text-muted-foreground"><Waves className="size-3.5" aria-hidden />Flood exposure</dt>
            {ctx.floodHotspots.length ? ctx.floodHotspots.map((h) => (
              <dd key={h.hotspotId}><SourceId id={h.hotspotId} /> {h.distanceM} m · {h.severity}{h.tideSensitive ? " · tide-sensitive" : ""}</dd>
            )) : <dd className="text-muted-foreground">No mapped hotspot</dd>}
          </div>
          <div>
            <dt className="flex items-center gap-1 text-xs text-muted-foreground"><CloudRain className="size-3.5" aria-hidden />Heavy rain (≥60 mm) near repair</dt>
            <dd>{heavy.length ? heavy.map((r) => `${fmtDate(r.date)}: ${r.rainfallMm} mm`).join(" · ") : "None recorded"}</dd>
            {ctx.tideAlerts.length > 0 && <dd className="text-xs text-muted-foreground">High-tide alerts: {ctx.tideAlerts.map((t) => fmtDate(t.date)).join(", ")}</dd>}
          </div>
          <div>
            <dt className="flex items-center gap-1 text-xs text-muted-foreground"><Hospital className="size-3.5" aria-hidden />Nearby facilities</dt>
            <dd>{ctx.facilitiesNearby.hospitals} hospital(s), {ctx.facilitiesNearby.schools} school(s) within 600 m</dd>
          </div>
        </dl>
        {rcAccidents.length > 0 && (
          <div>
            <div className="mb-1 text-xs text-muted-foreground">Road-condition accidents (correlation only, not causation)</div>
            <ul className="space-y-0.5">
              {rcAccidents.map((a) => (
                <li key={a.accidentId} className="flex flex-wrap items-center gap-1.5">
                  <SourceId id={a.accidentId} /> {fmtDate(a.date)} · {a.severity} · {a.vehicleType}
                  {a.afterCompletion && <span className="text-xs font-medium text-[oklch(0.45_0.12_60)]">after completion</span>}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
