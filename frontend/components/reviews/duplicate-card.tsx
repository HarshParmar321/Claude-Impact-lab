import { Check, X } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fmtDate, humanize, inr } from "@/lib/format";
import type { CaseDetail, WorkOrderFacts } from "@/lib/types";
import { SourceId } from "@/components/layout/badges";
import { cn } from "@/lib/utils";

const ROWS: [keyof WorkOrderFacts, string, (v: WorkOrderFacts) => React.ReactNode][] = [
  ["complaintId", "Linked complaint", (w) => (w.complaintId ? <SourceId id={w.complaintId} /> : <span className="font-medium text-[oklch(0.45_0.12_60)]">None</span>)],
  ["contractorName", "Contractor", (w) => w.contractorName],
  ["repairMethod", "Method", (w) => humanize(w.repairMethod)],
  ["areaSqm", "Area", (w) => `${w.areaSqm} sqm`],
  ["costInr", "Billed", (w) => inr(w.costInr)],
  ["issuedDate", "Issued", (w) => fmtDate(w.issuedDate)],
  ["completedDate", "Completed", (w) => fmtDate(w.completedDate)],
  ["photoBefore", "Before / after photo", (w) => `${w.photoBefore} / ${w.photoAfter}`],
  ["measurementBook", "Measurement book", (w) => w.measurementBook],
];

export function DuplicateCard({ dup, focusId }: { dup: NonNullable<CaseDetail["duplicate"]>; focusId: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Duplicate-like records</CardTitle>
        <CardDescription>{dup.label}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-muted-foreground">
                <th className="py-1 pr-2 font-medium" />
                {dup.sideBySide.map((w) => (
                  <th key={w.workOrderId} className={cn("py-1 pr-2 font-medium", w.workOrderId === focusId && "text-primary")}>
                    <SourceId id={w.workOrderId} className={w.workOrderId === focusId ? "bg-accent text-primary" : ""} />
                    <div className="mt-0.5 text-[11px]">{w.workOrderId === dup.flaggedId ? "Flagged record" : "Earlier record"}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map(([k, label, render]) => (
                <tr key={k} className="border-t">
                  <td className="py-1.5 pr-2 text-xs text-muted-foreground">{label}</td>
                  {dup.sideBySide.map((w) => <td key={w.workOrderId} className="py-1.5 pr-2 tabular-nums">{render(w)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <ul className="grid gap-1 text-sm sm:grid-cols-2">
          {dup.criteria.map((c) => (
            <li key={c.label} className="flex items-start gap-1.5">
              {c.met ? <Check className="mt-0.5 size-4 text-release" aria-label="met" /> : <X className="mt-0.5 size-4 text-muted-foreground" aria-label="not met" />}
              <span>
                {c.label}
                {c.detail && <span className="text-muted-foreground"> — {c.detail}</span>}
              </span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
