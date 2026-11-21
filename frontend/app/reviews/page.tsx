"use client";

import { Suspense, useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ArrowRight, Sparkles } from "lucide-react";
import { api, type ReviewFilters } from "@/lib/api";
import { inr, num, ratio, RULE_LABEL, VERDICT_LABEL, humanize } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ConfidenceBadge, RuleBadge, VerdictBadge } from "@/components/layout/badges";
import { EmptyState, ErrorState, LoadingBlock, PageHeader } from "@/components/layout/states";

const PAGE = 25;

function ReviewInbox() {
  const sp = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const filters: ReviewFilters = useMemo(
    () => ({
      ward: sp.get("ward") || undefined,
      contractor: sp.get("contractor") || undefined,
      rule: sp.get("rule") || undefined,
      verdict: sp.get("verdict") || undefined,
      repair_method: sp.get("repair_method") || undefined,
      include_data_quality: sp.get("include_data_quality") === "true" || undefined,
      q: sp.get("q") || undefined,
      limit: PAGE,
      offset: Number(sp.get("offset") || 0),
    }),
    [sp],
  );
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["reviews", filters],
    queryFn: () => api.reviews(filters),
    placeholderData: keepPreviousData,
  });

  const set = (key: string, value: string) => {
    const p = new URLSearchParams(sp.toString());
    if (value) p.set(key, value);
    else p.delete(key);
    if (key !== "offset") p.delete("offset");
    router.replace(`${pathname}?${p.toString()}`, { scroll: false });
  };

  return (
    <div className="space-y-4">
      <PageHeader
        title="Review Inbox"
        description="Deduplicated review leads: each work order appears once with every rule it triggered. Open a case to see the evidence trail and run the Fair Hearing."
      />

      <Card className="border-primary/30 bg-accent/60 py-3">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 text-sm">
          <div className="flex items-center gap-2">
            <Sparkles className="size-4 text-primary" aria-hidden />
            <span>
              <span className="font-medium">Demo case:</span> WO25-02469 · Sion Trombay Road · duplicate-like record on a road under DLP
            </span>
          </div>
          <Button size="sm" asChild>
            <Link href="/reviews/WO25-02469">
              Open case <ArrowRight />
            </Link>
          </Button>
        </CardContent>
      </Card>

      <div className="flex flex-wrap items-end gap-2" role="search" aria-label="Filter review leads">
        <Input
          aria-label="Search work order or road"
          placeholder="Search WO ID or road…"
          defaultValue={filters.q}
          className="w-56"
          onKeyDown={(e) => e.key === "Enter" && set("q", (e.target as HTMLInputElement).value)}
          onBlur={(e) => e.target.value !== (filters.q || "") && set("q", e.target.value)}
        />
        <NativeSelect aria-label="Ward" value={filters.ward || ""} onChange={(e) => set("ward", e.target.value)}>
          <option value="">All wards</option>
          {data?.filters.wards.map((w) => <option key={w} value={w}>{w}</option>)}
        </NativeSelect>
        <NativeSelect aria-label="Contractor" value={filters.contractor || ""} onChange={(e) => set("contractor", e.target.value)}>
          <option value="">All contractors</option>
          {data?.filters.contractors.map((c) => <option key={c.contractorId} value={c.contractorId}>{c.contractorName}</option>)}
        </NativeSelect>
        <NativeSelect aria-label="Repair method" value={filters.repair_method || ""} onChange={(e) => set("repair_method", e.target.value)}>
          <option value="">All methods</option>
          {data?.filters.repairMethods.map((m) => <option key={m} value={m}>{humanize(m)}</option>)}
        </NativeSelect>
        <NativeSelect aria-label="Rule" value={filters.rule || ""} onChange={(e) => set("rule", e.target.value)}>
          <option value="">All rules</option>
          {data?.filters.rules.map((r) => <option key={r} value={r}>{RULE_LABEL[r]}</option>)}
        </NativeSelect>
        <NativeSelect aria-label="Verdict" value={filters.verdict || ""} onChange={(e) => set("verdict", e.target.value)}>
          <option value="">All verdicts</option>
          {data?.filters.verdicts.map((v) => <option key={v} value={v}>{VERDICT_LABEL[v]}</option>)}
        </NativeSelect>
        <label className="flex h-9 items-center gap-2 rounded-md border bg-card px-2.5 text-sm">
          <input type="checkbox" checked={!!filters.include_data_quality} onChange={(e) => set("include_data_quality", e.target.checked ? "true" : "")} />
          Include data-quality flags
        </label>
        {(filters.ward || filters.contractor || filters.rule || filters.verdict || filters.repair_method || filters.q || filters.include_data_quality) && (
          <Button variant="ghost" size="sm" onClick={() => router.replace(pathname)}>Clear</Button>
        )}
      </div>

      {isLoading ? (
        <LoadingBlock rows={6} />
      ) : error || !data ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : data.items.length === 0 ? (
        <EmptyState title="No review leads match these filters" detail="Try clearing a filter." />
      ) : (
        <Card className="py-0">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2.5 text-sm">
            <span>
              <span className="font-semibold tabular-nums">{num(data.total)}</span> work orders ·{" "}
              <span className="tabular-nums">{inr(data.amountRequiringReviewInr)}</span> requiring review (not confirmed loss)
            </span>
            {isFetching && <span className="text-xs text-muted-foreground">Updating…</span>}
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Work order</TableHead>
                <TableHead>Ward</TableHead>
                <TableHead>Road</TableHead>
                <TableHead>Contractor</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead className="text-right">vs rate card</TableHead>
                <TableHead>Rules triggered</TableHead>
                <TableHead>Confidence</TableHead>
                <TableHead>Recommended verdict</TableHead>
                <TableHead><span className="sr-only">Open</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((l) => (
                <TableRow key={l.workOrderId} className={l.workOrderId === "WO25-02469" ? "bg-accent/40" : undefined}>
                  <TableCell className="font-mono text-xs">{l.workOrderId}</TableCell>
                  <TableCell>{l.wardCode}</TableCell>
                  <TableCell className="max-w-48 truncate" title={l.roadName}>{l.roadName}</TableCell>
                  <TableCell className="max-w-40 truncate" title={l.contractorName}>{l.contractorName}</TableCell>
                  <TableCell className="text-right tabular-nums">{inr(l.amountInr)}</TableCell>
                  <TableCell className="text-right tabular-nums">{ratio(l.rateRatio)}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">{l.rules.map((r) => <RuleBadge key={r} rule={r} />)}</div>
                  </TableCell>
                  <TableCell><ConfidenceBadge confidence={l.confidence} /></TableCell>
                  <TableCell>
                    <div className="flex flex-col gap-0.5">
                      <VerdictBadge verdict={l.finalVerdict ?? l.recommendedVerdict} />
                      <span className="text-[11px] text-muted-foreground">{l.finalVerdict ? "Officer decision" : "Awaiting officer"}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Button size="sm" variant="outline" asChild>
                      <Link href={`/reviews/${l.workOrderId}`}>Open case</Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="flex items-center justify-between border-t px-4 py-2.5 text-sm">
            <span className="text-muted-foreground">
              {data.offset + 1}–{Math.min(data.offset + PAGE, data.total)} of {num(data.total)}
            </span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" disabled={data.offset === 0} onClick={() => set("offset", String(Math.max(0, data.offset - PAGE)))}>Previous</Button>
              <Button size="sm" variant="outline" disabled={data.offset + PAGE >= data.total} onClick={() => set("offset", String(data.offset + PAGE))}>Next</Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

export default function ReviewsPage() {
  return (
    <Suspense fallback={<LoadingBlock rows={6} />}>
      <ReviewInbox />
    </Suspense>
  );
}
