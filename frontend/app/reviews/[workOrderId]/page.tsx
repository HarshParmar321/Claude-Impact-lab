"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, MessageSquareWarning, QrCode } from "lucide-react";
import { api } from "@/lib/api";
import { fmtDate, humanize, inr } from "@/lib/format";
import type { Hearing } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfidenceBadge, RuleBadge, SourceId, SourceList, VerdictBadge } from "@/components/layout/badges";
import { ErrorState, LoadingBlock } from "@/components/layout/states";
import { EvidenceTimeline } from "@/components/reviews/evidence-timeline";
import { ComplaintList } from "@/components/reviews/complaint-list";
import { CostCard } from "@/components/reviews/cost-card";
import { DuplicateCard } from "@/components/reviews/duplicate-card";
import { DlpContextCard } from "@/components/reviews/dlp-context-card";
import { FairHearingPanel } from "@/components/hearing/fair-hearing-panel";
import { DecisionPanel } from "@/components/hearing/decision-panel";

export default function CasePage({ params }: { params: Promise<{ workOrderId: string }> }) {
  const { workOrderId } = use(params);
  const id = decodeURIComponent(workOrderId);
  const { data: c, isLoading, error, refetch } = useQuery({ queryKey: ["case", id], queryFn: () => api.review(id) });
  const [hearing, setHearing] = useState<Hearing | null>(null);

  if (isLoading) return <LoadingBlock rows={6} />;
  if (error || !c) return <ErrorState error={error} onRetry={() => refetch()} />;
  const w = c.workOrder;

  return (
    <div className="space-y-5">
      <Link href="/reviews" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Review Inbox
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="font-mono text-2xl font-semibold">{w.workOrderId}</h1>
            <VerdictBadge verdict={c.lead.finalVerdict ?? c.recommendedVerdict} />
            <span className="text-xs text-muted-foreground">{c.lead.finalVerdict ? "Officer decision" : "Recommended · awaiting officer"}</span>
          </div>
          <p className="text-sm">
            {w.roadName} · Ward {w.wardCode} · {w.contractorName} · {humanize(w.workType)} ({humanize(w.repairMethod)}) · {w.areaSqm} sqm ·{" "}
            <span className="font-semibold tabular-nums">{inr(w.costInr)}</span> · completed {fmtDate(w.completedDate)}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {c.rules.length ? c.rules.map((r) => <RuleBadge key={r} rule={r} />) : <span className="text-sm text-muted-foreground">No review rule triggered</span>}
            <ConfidenceBadge confidence={c.confidence} />
            <span className="text-xs text-muted-foreground">Counts as {c.lead.leadCount} review lead</span>
          </div>
        </div>
        <Button variant="outline" asChild>
          <Link href={`/receipt/${w.workOrderId}`}><QrCode />Public Receipt</Link>
        </Button>
      </div>

      {c.recordConflicts.length > 0 && (
        <Card className="border-hold/40 bg-hold-bg/40">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base"><AlertTriangle className="size-4" aria-hidden />Record conflicts ({c.recordConflicts.length})</CardTitle>
            <CardDescription>Deterministic checks across complaints, work orders and road signals. Conflicts call for verification; they are not findings.</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {c.recordConflicts.map((rc, i) => (
                <li key={i} className="flex flex-col gap-0.5">
                  <span><span className="font-medium">{humanize(rc.type)}:</span> {rc.text}</span>
                  <span className="flex flex-wrap gap-1">{rc.sourceIds.map((s) => <SourceId key={s} id={s} />)}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-5 lg:grid-cols-12">
        <div className="space-y-5 lg:col-span-7">
          <Card>
            <CardHeader>
              <CardTitle>Complaint-to-payment evidence timeline</CardTitle>
              <CardDescription>Complaint → issue → work order → road → rate card → ward → verdict</CardDescription>
            </CardHeader>
            <CardContent>
              <EvidenceTimeline events={c.timeline} focusId={w.workOrderId} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><MessageSquareWarning className="size-4" aria-hidden />Citizen complaints on this road</CardTitle>
              <CardDescription>Original language with the dataset&apos;s English translation · linked and same-issue complaints from 14 days before issue to 30 days after completion</CardDescription>
            </CardHeader>
            <CardContent>
              <ComplaintList complaints={c.complaints} />
            </CardContent>
          </Card>
        </div>
        <div className="space-y-5 lg:col-span-5">
          <CostCard rate={c.rateCheck} />
          {c.duplicate && <DuplicateCard dup={c.duplicate} focusId={w.workOrderId} />}
          <DlpContextCard dlp={c.dlp} ctx={c.context} />
          <Card className="gap-2 py-4">
            <CardContent className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium">Evidence completeness</span>
                <span className="tabular-nums font-semibold">{c.evidenceCompleteness.scorePct}%</span>
              </div>
              <div className="text-xs text-muted-foreground">
                Present: {c.evidenceCompleteness.present.join(", ") || "none"} · Missing: {c.evidenceCompleteness.missing.join(", ") || "none"}
              </div>
              <div className="text-xs text-muted-foreground">Photo fields are Y/N flags in the dataset; no images were verified.</div>
            </CardContent>
          </Card>
        </div>
      </div>

      <FairHearingPanel workOrderId={w.workOrderId} onResult={setHearing} />
      <DecisionPanel c={c} hearing={hearing} />

      {c.durabilityFeedback.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Citizen durability reports</CardTitle>
            <CardDescription>From the Public Repair Receipt</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1.5 text-sm">
              {c.durabilityFeedback.map((f) => (
                <li key={f.id} className="flex flex-wrap items-center gap-2">
                  <span className="text-xs text-muted-foreground">{fmtDate(f.createdAt)}</span>
                  <span className="font-medium">{humanize(f.answer)}</span>
                  {f.caseReference && <SourceId id={f.caseReference} />}
                  {f.routedTo && <span className="text-muted-foreground">→ {f.routedTo}</span>}
                  {f.description && <span className="text-muted-foreground">“{f.description}”</span>}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <Card className="bg-muted/40 py-4">
        <CardContent className="space-y-2 text-xs text-muted-foreground">
          <div className="font-medium text-foreground">Data limitations</div>
          <ul className="list-disc pl-5">{c.dataLimitations.map((d) => <li key={d}>{d}</li>)}</ul>
          <SourceList ids={c.sourceIds} label="All source records in this case" />
        </CardContent>
      </Card>
    </div>
  );
}
