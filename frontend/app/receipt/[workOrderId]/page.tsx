"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { QRCodeSVG } from "qrcode.react";
import { BadgeCheck, PauseCircle, ShieldQuestion } from "lucide-react";
import { api } from "@/lib/api";
import { fmtDate, inr } from "@/lib/format";
import type { Language, Verdict } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { SourceId } from "@/components/layout/badges";
import { ErrorState, LoadingBlock } from "@/components/layout/states";
import { DurabilityFeedbackForm } from "@/components/receipt/durability-feedback";
import { AskBox } from "@/components/receipt/ask-box";
import { cn } from "@/lib/utils";

const LANGS: { code: Language; label: string }[] = [
  { code: "mr", label: "मराठी" },
  { code: "hi", label: "हिन्दी" },
  { code: "hinglish", label: "Hinglish" },
  { code: "en", label: "English" },
];

const STATUS_STYLE: Record<Verdict, { cls: string; Icon: typeof BadgeCheck }> = {
  RELEASE_PAYMENT: { cls: "border-release/40 bg-release-bg text-release", Icon: BadgeCheck },
  HOLD_FOR_EVIDENCE: { cls: "border-hold/40 bg-hold-bg text-[oklch(0.42_0.11_60)]", Icon: PauseCircle },
  WARRANTY_REVIEW: { cls: "border-warranty/40 bg-warranty-bg text-warranty", Icon: ShieldQuestion },
};

export default function ReceiptPage({ params }: { params: Promise<{ workOrderId: string }> }) {
  const { workOrderId } = use(params);
  const id = decodeURIComponent(workOrderId);
  const [lang, setLang] = useState<Language>("en");
  const [url, setUrl] = useState("");
  useEffect(() => setUrl(window.location.href), []);
  const { data: r, isLoading, error, refetch } = useQuery({ queryKey: ["receipt", id, lang], queryFn: () => api.receipt(id, lang) });

  return (
    <div className="space-y-4" lang={lang === "hinglish" ? "hi-Latn" : lang}>
      <div className="flex gap-1 rounded-lg bg-muted p-1" role="group" aria-label="Language">
        {LANGS.map((l) => (
          <button
            key={l.code}
            onClick={() => setLang(l.code)}
            aria-pressed={lang === l.code}
            className={cn("flex-1 rounded-md px-2 py-1.5 text-sm font-medium", lang === l.code ? "bg-card shadow-sm" : "text-muted-foreground")}
          >
            {l.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <LoadingBlock rows={4} />
      ) : error || !r ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : (
        <>
          <div>
            <h1 className="text-xl font-semibold">{r.labels.title}</h1>
            <p className="font-mono text-sm text-muted-foreground">{r.workOrderId}</p>
          </div>

          {(() => {
            const s = STATUS_STYLE[r.verdict];
            return (
              <div className={cn("rounded-xl border-2 p-4", s.cls)} role="status">
                <div className="text-xs font-medium uppercase tracking-wide opacity-80">{r.labels.status}</div>
                <div className="mt-1 flex items-start gap-2 text-base font-semibold">
                  <s.Icon className="mt-0.5 size-5 shrink-0" aria-hidden />
                  {r.statusText}
                </div>
                <div className="mt-1 text-xs opacity-80">{r.statusSource}</div>
              </div>
            );
          })()}

          <Card className="gap-3 py-4">
            <CardContent className="space-y-2">
              <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{r.labels.complaint}</div>
              <p className="text-sm font-medium">{r.complaintSummary}</p>
              {r.complaint && (
                <div className="rounded-lg bg-muted/60 p-2.5 text-sm">
                  <div className="mb-1 text-[11px] text-muted-foreground">{r.labels.original} · <SourceId id={r.complaint.complaintId} /></div>
                  {r.complaint.textOriginal}
                </div>
              )}
            </CardContent>
          </Card>

          {r.related && (
            <Link href={`/receipt/${r.related.workOrderId}`} className="block rounded-xl border border-dashed bg-card p-3 text-sm hover:bg-accent">
              <div className="text-xs text-muted-foreground">{r.related.relation}</div>
              <div className="mt-1 flex items-center justify-between gap-2">
                <span className="font-mono text-xs">{r.related.workOrderId}</span>
                <span className="tabular-nums">{fmtDate(r.related.completedDate)} · {inr(r.related.amountInr)}</span>
              </div>
              <div className="mt-1">{r.related.complaintSummary}</div>
            </Link>
          )}

          <Card className="py-2">
            <CardContent>
              <dl className="divide-y text-sm">
                {[
                  [r.labels.road, `${r.roadName}`],
                  [r.labels.ward, r.wardCode],
                  [r.labels.contractor, r.contractorName],
                  [r.labels.method, r.repairMethod],
                  [r.labels.completed, fmtDate(r.completedDate)],
                  [r.labels.amount, inr(r.amountInr)],
                  [r.labels.sla, r.slaMet ? `✓ ${r.labels.yes}` : `! ${r.labels.no}`],
                  [r.labels.reopened, r.reopenedWithin30d ? `! ${r.labels.yes}` : `✓ ${r.labels.no}`],
                  [r.labels.dlp, r.dlp.text],
                  [r.labels.evidence, `${r.evidenceCompletenessPct}%`],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-4 py-2">
                    <dt className="text-muted-foreground">{k}</dt>
                    <dd className="text-right font-medium tabular-nums">{v}</dd>
                  </div>
                ))}
              </dl>
            </CardContent>
          </Card>

          <Card className="gap-3 py-4">
            <CardContent className="space-y-3">
              <h2 className="text-lg font-semibold">{r.labels.surviveQ}</h2>
              <DurabilityFeedbackForm r={r} language={lang} />
              <p className="text-xs text-muted-foreground">
                ✓ {r.feedbackCounts.SURVIVED} · ✗ {r.feedbackCounts.FAILED} · ? {r.feedbackCounts.UNSURE}
                {r.warrantyCases.length > 0 && <> · {r.warrantyCases.map((w) => w.caseReference).join(", ")}</>}
              </p>
            </CardContent>
          </Card>

          <Card className="gap-3 py-4">
            <CardContent className="space-y-2">
              <h2 className="text-sm font-semibold">{r.labels.ask}</h2>
              <AskBox workOrderId={r.workOrderId} language={lang} label={r.labels.ask} />
            </CardContent>
          </Card>

          <div className="flex items-start gap-3 rounded-xl border bg-card p-3">
            {url && <QRCodeSVG value={url} size={84} aria-label="QR code linking to this receipt" />}
            <p className="text-xs text-muted-foreground">{r.qrNote}</p>
          </div>

          <p className="text-xs text-muted-foreground">{r.labels.disclaimer}</p>
          <div className="flex flex-wrap gap-1 text-xs text-muted-foreground">
            {r.labels.sources}: {r.sourceIds.map((s) => <SourceId key={s} id={s} />)}
          </div>
        </>
      )}
    </div>
  );
}
