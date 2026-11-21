"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Info, Link2, ListChecks, ShieldQuestion, Wallet } from "lucide-react";
import { api } from "@/lib/api";
import { inr, inrCompact, num, pct, RULE_LABEL, humanize } from "@/lib/format";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/dashboard/stat-card";
import { FlowSankey } from "@/components/dashboard/flow-sankey";
import { RoadMap, type MapPoint } from "@/components/map/road-map";
import { ErrorState, LoadingBlock, PageHeader } from "@/components/layout/states";
import type { ReviewRule } from "@/lib/types";

export default function OverviewPage() {
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ["summary"], queryFn: api.summary });

  if (isLoading) return <LoadingBlock rows={5} />;
  if (error || !data) return <ErrorState error={error} onRetry={() => refetch()} />;
  const c = data.cards;

  const points: MapPoint[] = [
    ...data.map.priorityPoints.map((p) => ({
      id: p.roadId, lat: p.lat, lon: p.lon, kind: "priority" as const, title: `${p.roadName} (${p.wardCode})`,
      lines: [`Priority score ${p.priorityScore}/100`, p.underDlp ? "Under DLP" : "Not under DLP"], weight: 2,
    })),
    ...data.map.leadPoints.map((p) => ({
      id: p.roadId, lat: p.lat, lon: p.lon, kind: "lead" as const, title: `${p.roadName} (${p.wardCode})`,
      lines: [`${p.leads} review lead(s) · ${inr(p.amountInr)} requiring review`, p.workOrderIds.join(", ")],
      href: `/reviews/${p.workOrderIds[0]}`, weight: p.leads,
    })),
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="City overview"
        description="NagarLens connects complaints, work orders, roads, rate cards and wards into one money trail. Every figure below is computed in Python and traceable to source records."
      >
        <Button asChild>
          <Link href="/reviews">
            Open Review Inbox <ArrowRight />
          </Link>
        </Button>
      </PageHeader>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard icon={<ListChecks className="size-3.5" />} label="Unique review leads" value={num(c.uniqueReviewLeads)}
          hint={<>Each work order counted once · {c.leadsWithMultipleRules} trigger 2+ rules</>} />
        <StatCard icon={<Wallet className="size-3.5" />} label="Amount requiring review" value={inrCompact(c.amountRequiringReviewInr)}
          hint="Requires review — not a confirmed loss" />
        <StatCard icon={<Link2 className="size-3.5" />} label="Complaint → work-order linkage" value={pct(c.linkageRatePct)}
          hint={`of ${num(c.workOrders)} work orders cite a complaint`} />
        <StatCard icon={<ShieldQuestion className="size-3.5" />} label="DLP review" value={num(c.dlpReviewCount)}
          hint="Paid repairs on roads under warranty → Ward Warranty Desk" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Rule hits (not additive)</CardTitle>
          <CardDescription>
            A work order caught by several rules is one lead with several reasons. These counts overlap and must not be summed.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2 text-sm">
          {(Object.keys(c.ruleHits) as ReviewRule[]).map((r) => (
            <Link key={r} href={`/reviews?rule=${r}`} className="rounded-md border bg-card px-3 py-1.5 hover:bg-accent">
              {RULE_LABEL[r]}: <span className="font-semibold tabular-nums">{num(c.ruleHits[r])}</span>
              {r === "LOW_COST_DATA_QUALITY" && <span className="text-muted-foreground"> (data quality, not a lead)</span>}
            </Link>
          ))}
          <span className="rounded-md border border-dashed px-3 py-1.5 text-muted-foreground">
            Context band 1.30–1.40×: {num(c.contextBandOrders)} (shown, not counted)
          </span>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Money trail</CardTitle>
            <CardDescription>Complaints → issue → work-order linkage → payment verdict</CardDescription>
          </CardHeader>
          <CardContent>
            <FlowSankey data={data.sankey} />
          </CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Review leads and priority roads</CardTitle>
            <CardDescription>Click a marker for record IDs</CardDescription>
          </CardHeader>
          <CardContent>
            <RoadMap points={points} height={360} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Ward accountability</CardTitle>
            <CardDescription>Lowest composite ward scores and their largest system/process issue</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {data.wardSummary.map((w) => (
              <Link key={w.wardCode} href={`/scorecards?tab=wards&ward=${encodeURIComponent(w.wardCode)}`}
                className="flex items-center justify-between rounded-md border px-3 py-2 text-sm hover:bg-accent">
                <span>
                  <span className="font-medium">{w.wardName}</span>
                  <span className="block text-xs text-muted-foreground">Largest system issue: {humanize(w.mainSystemIssue)} · {w.uniqueReviewLeads} leads</span>
                </span>
                <span className="tabular-nums font-semibold">{w.overallScore}</span>
              </Link>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Contractor accountability</CardTitle>
            <CardDescription>Below peers on SLA or durability, compared within the same method and SLA tier</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {data.contractorSummary.belowPeersOnDelivery.slice(0, 5).map((ct) => (
              <Link key={ct.contractorId} href={`/scorecards?tab=contractors&contractor=${ct.contractorId}`}
                className="flex items-center justify-between rounded-md border px-3 py-2 text-sm hover:bg-accent">
                <span className="font-medium">{ct.contractorName}</span>
                <span className="text-xs text-muted-foreground tabular-nums">
                  SLA {ct.slaGap > 0 ? "+" : ""}{ct.slaGap} pts · durability {ct.durabilityGap > 0 ? "+" : ""}{ct.durabilityGap} pts · n={ct.sampleSize}
                </span>
              </Link>
            ))}
            <p className="pt-1 text-xs text-muted-foreground">
              {num(data.contractorSummary.dlpLeadsNotAttributed)} DLP review leads are not attributed to any contractor until the original warranty owner is identified.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card className="bg-muted/40">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm"><Info className="size-4" /> Methodology</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
            {data.methodology.map((m) => <li key={m}>{m}</li>)}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
