"use client";

import { Fragment, useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronRight, TriangleAlert } from "lucide-react";
import type { ContractorScore, ScorecardMethodology } from "@/lib/types";
import { camelLabel, humanize, pct } from "@/lib/format";
import { ConfidenceBadge, SourceId } from "@/components/layout/badges";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

function Gap({ v }: { v: number | null }) {
  if (v === null) return <span className="text-muted-foreground">n/a</span>;
  const better = v > 0.5;
  const worse = v < -0.5;
  return (
    <span className={cn("text-xs tabular-nums", better && "text-release", worse && "text-[oklch(0.45_0.12_60)]")}>
      {better ? "▲" : worse ? "▼" : "•"} {v > 0 ? "+" : ""}{v.toFixed(1)} vs peers
    </span>
  );
}

function Dim({ value, gap }: { value: number | null; gap: number | null }) {
  return (
    <div className="flex flex-col">
      <span className="tabular-nums">{pct(value)}</span>
      <Gap v={gap} />
    </div>
  );
}

export function ContractorTable({ items, methodology, initial }: { items: ContractorScore[]; methodology: ScorecardMethodology; initial?: string }) {
  const [open, setOpen] = useState<string | null>(initial ?? null);
  return (
    <div className="space-y-3">
      <div className="rounded-lg border bg-muted/40 p-3 text-xs text-muted-foreground">
        <p><span className="font-medium text-foreground">Peer groups:</span> {methodology.peerGroup}</p>
        <p><span className="font-medium text-foreground">Sample confidence:</span> {methodology.confidence}</p>
        <p><span className="font-medium text-foreground">Not scored:</span> {methodology.notScoredAgainstContractors}</p>
        <p className="mt-1">Listed alphabetically by ID, not ranked. Expand a row for each comparison group, its sample size and the records behind the score.</p>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead />
            <TableHead>Contractor</TableHead>
            <TableHead className="text-right">Jobs</TableHead>
            <TableHead>Sample</TableHead>
            {Object.keys(methodology.contractorDimensions).map((k) => (
              <TableHead key={k} title={methodology.contractorDimensions[k]}>{camelLabel(k)}</TableHead>
            ))}
            <TableHead>Open leads (not scored)</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((c) => {
            const isOpen = open === c.contractorId;
            return (
              <Fragment key={c.contractorId}>
                <TableRow className="cursor-pointer" onClick={() => setOpen(isOpen ? null : c.contractorId)} aria-expanded={isOpen}>
                  <TableCell>{isOpen ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}</TableCell>
                  <TableCell>
                    <div className="font-medium">{c.contractorName}</div>
                    <SourceId id={c.contractorId} />
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{c.sampleSize}</TableCell>
                  <TableCell><ConfidenceBadge confidence={c.confidence} label="sample" /></TableCell>
                  <TableCell><Dim value={c.dimensions.slaReliability} gap={c.gapVsPeers.slaReliability} /></TableCell>
                  <TableCell><Dim value={c.dimensions.durability} gap={c.gapVsPeers.durability} /></TableCell>
                  <TableCell><Dim value={c.dimensions.rateAlignment} gap={c.gapVsPeers.rateAlignment} /></TableCell>
                  <TableCell><Dim value={c.dimensions.evidenceCompleteness} gap={c.gapVsPeers.evidenceCompleteness} /></TableCell>
                  <TableCell className="text-xs">
                    {c.openReviewLeads.count} · DLP {c.openReviewLeads.dlpReviewNotAttributed} · dup {c.openReviewLeads.possibleDuplicatesNotScored}
                  </TableCell>
                </TableRow>
                {isOpen && (
                  <TableRow className="hover:bg-transparent">
                    <TableCell colSpan={9} className="whitespace-normal bg-muted/30 p-4">
                      <div className="space-y-3">
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs">
                            <thead className="text-left text-muted-foreground">
                              <tr>
                                <th className="py-1 pr-3 font-medium">Peer group (method · SLA tier)</th>
                                <th className="py-1 pr-3 font-medium">n / peer n</th>
                                <th className="py-1 pr-3 font-medium">SLA (peer)</th>
                                <th className="py-1 pr-3 font-medium">Durability (peer)</th>
                                <th className="py-1 pr-3 font-medium">Rate alignment (peer)</th>
                                <th className="py-1 pr-3 font-medium">Evidence (peer)</th>
                              </tr>
                            </thead>
                            <tbody>
                              {c.peerGroups.map((g) => (
                                <tr key={g.peerGroup} className="border-t">
                                  <td className="py-1.5 pr-3">
                                    {humanize(g.repairMethod)} · {g.slaTier}
                                    {g.lowSampleWarning && (
                                      <span className="ml-2 inline-flex items-center gap-1 text-[oklch(0.45_0.12_60)]"><TriangleAlert className="size-3" />low sample</span>
                                    )}
                                  </td>
                                  <td className="py-1.5 pr-3 tabular-nums">{g.sampleSize} / {g.peerSampleSize} ({g.peerContractors} contractors)</td>
                                  <td className="py-1.5 pr-3 tabular-nums">{pct(g.slaReliability)} ({pct(g.peerSlaReliability)})</td>
                                  <td className="py-1.5 pr-3 tabular-nums">{pct(g.durability)} ({pct(g.peerDurability)})</td>
                                  <td className="py-1.5 pr-3 tabular-nums">{pct(g.rateAlignment)} ({pct(g.peerRateAlignment)})</td>
                                  <td className="py-1.5 pr-3 tabular-nums">{pct(g.evidenceCompleteness)} ({pct(g.peerEvidenceCompleteness)})</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                        <div className="grid gap-2 text-xs sm:grid-cols-3">
                          {([["SLA breaches", c.evidenceLinks.slaBreaches], ["Reopened within 30 days", c.evidenceLinks.reopened], ["Outside 0.75–1.30× rate range", c.evidenceLinks.outsideRateRange]] as const).map(([label, ids]) => (
                            <div key={label}>
                              <div className="mb-1 text-muted-foreground">{label} (sample records)</div>
                              <div className="flex flex-wrap gap-1">
                                {ids.length ? ids.map((i) => <Link key={i} href={`/reviews/${i}`}><SourceId id={i} className="hover:text-primary" /></Link>) : "—"}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </TableCell>
                  </TableRow>
                )}
              </Fragment>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
