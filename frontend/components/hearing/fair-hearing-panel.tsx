"use client";

import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Gavel, Loader2, Scale, Search, ShieldCheck, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import type { Hearing } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ConfidenceBadge, SourceList, VerdictBadge } from "@/components/layout/badges";
import { ErrorState } from "@/components/layout/states";
import { cn } from "@/lib/utils";

const MODE = {
  live: { label: "Live Claude", detail: "Generated now by the backend via the Anthropic API" },
  cache: { label: "Cached Claude response", detail: "Served from the committed cache (matched by evidence hash)" },
  template: { label: "Deterministic template", detail: "Assembled from the audit rules because Claude was unavailable" },
} as const;

export function FairHearingPanel({ workOrderId, onResult }: { workOrderId: string; onResult?: (h: Hearing) => void }) {
  const [stage, setStage] = useState(0);
  const m = useMutation({
    mutationFn: (forceTemplate: boolean) => api.hearing(workOrderId, forceTemplate),
    onSuccess: (h) => {
      setStage(0);
      onResult?.(h);
    },
  });

  // Reveal Auditor → Fairness Advocate → Verdict so the hearing is visible on screen.
  useEffect(() => {
    if (!m.data) return;
    const timers = [setTimeout(() => setStage(1), 150), setTimeout(() => setStage(2), 900), setTimeout(() => setStage(3), 1650)];
    return () => timers.forEach(clearTimeout);
  }, [m.data]);

  const h = m.data;
  return (
    <Card className="border-primary/30">
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle className="flex items-center gap-2"><Scale className="size-5 text-primary" aria-hidden />Claude Fair Hearing</CardTitle>
          <CardDescription className="max-w-2xl">
            Claude receives only the structured evidence above (Python-computed figures and source IDs). It argues the strongest case for review, then the strongest legitimate context, then recommends one verdict.
          </CardDescription>
        </div>
        <div className="flex gap-2">
          {h && (
            <Button variant="ghost" size="sm" onClick={() => m.mutate(true)} disabled={m.isPending} title="Show the deterministic fallback for comparison">
              Show template
            </Button>
          )}
          <Button onClick={() => m.mutate(false)} disabled={m.isPending}>
            {m.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
            {h ? "Re-run hearing" : "Run Fair Hearing"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {m.isError && <ErrorState error={m.error} onRetry={() => m.mutate(false)} />}
        {!h && !m.isPending && !m.isError && (
          <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
            Run the hearing to see the Auditor and the Fairness Advocate present both sides. The UI works with or without an Anthropic API key.
          </p>
        )}
        {m.isPending && <p className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" />Hearing both sides…</p>}
        {h && (
          <>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Badge variant={h.mode === "live" ? "release" : h.mode === "cache" ? "secondary" : "hold"}>{MODE[h.mode].label}</Badge>
              <span className="text-muted-foreground">{MODE[h.mode].detail} · {h.origin}</span>
              <code className="text-muted-foreground" title="SHA-256 of the structured evidence">#{h.evidenceHash.slice(0, 10)}</code>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <section aria-label="Auditor case" className={cn("rounded-xl border p-4 transition-all duration-500", stage >= 1 ? "opacity-100" : "translate-y-2 opacity-0")}>
                <h3 className="mb-2 flex items-center gap-2 font-semibold"><Search className="size-4 text-[oklch(0.45_0.12_60)]" aria-hidden />Auditor</h3>
                <p className="text-sm font-medium">{h.auditorCase.summary}</p>
                <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm">
                  {h.auditorCase.evidence.map((e) => <li key={e}>{e}</li>)}
                </ul>
                <div className="mt-3"><SourceList ids={h.auditorCase.sourceIds} /></div>
              </section>
              <section aria-label="Fairness Advocate case" className={cn("rounded-xl border p-4 transition-all duration-500", stage >= 2 ? "opacity-100" : "translate-y-2 opacity-0")}>
                <h3 className="mb-2 flex items-center gap-2 font-semibold"><ShieldCheck className="size-4 text-release" aria-hidden />Fairness Advocate</h3>
                <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Possible legitimate context</div>
                <ul className="mt-1 list-disc space-y-1.5 pl-5 text-sm">
                  {h.fairnessCase.possibleLegitimateContext.map((e) => <li key={e}>{e}</li>)}
                </ul>
                <div className="mt-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">Limitations</div>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                  {h.fairnessCase.limitations.map((e) => <li key={e}>{e}</li>)}
                </ul>
                <div className="mt-3"><SourceList ids={h.fairnessCase.sourceIds} /></div>
              </section>
            </div>
            <section aria-label="Recommendation" className={cn("rounded-xl border bg-muted/40 p-4 transition-all duration-500", stage >= 3 ? "opacity-100" : "translate-y-2 opacity-0")}>
              <div className="flex flex-wrap items-center gap-3">
                <Gavel className="size-4" aria-hidden />
                <span className="font-semibold">Recommendation</span>
                <VerdictBadge verdict={h.recommendedVerdict} />
                <ConfidenceBadge confidence={h.confidence} />
                {h.verdictDiffersFromRules && <Badge variant="hold">Differs from rule-based verdict — officer to decide</Badge>}
              </div>
              <p className="mt-2 text-sm">{h.reasoning}</p>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <div className="rounded-lg bg-card p-3 text-sm">
                  <div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Officer brief</div>
                  {h.officerBrief}
                </div>
                <div className="rounded-lg bg-card p-3 text-sm">
                  <div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Citizen explanation</div>
                  {h.citizenExplanation}
                </div>
              </div>
              {h.notes.length > 0 && <p className="mt-2 text-xs text-muted-foreground">{h.notes.join(" ")}</p>}
            </section>
          </>
        )}
      </CardContent>
    </Card>
  );
}
