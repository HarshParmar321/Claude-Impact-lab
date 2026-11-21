"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { BadgeCheck, CheckCircle2, PauseCircle, QrCode, ShieldQuestion } from "lucide-react";
import { api } from "@/lib/api";
import { fmtDate, VERDICT_LABEL } from "@/lib/format";
import type { CaseDetail, Hearing, Verdict } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { VerdictBadge } from "@/components/layout/badges";
import { cn } from "@/lib/utils";

const OPTIONS: { v: Verdict; title: string; Icon: typeof BadgeCheck; ring: string; sub: (c: CaseDetail) => string }[] = [
  { v: "RELEASE_PAYMENT", title: "Release Payment", Icon: BadgeCheck, ring: "border-release bg-release-bg", sub: () => "No material rule remains unresolved, or evidence explains the lead." },
  { v: "HOLD_FOR_EVIDENCE", title: "Hold for Evidence", Icon: PauseCircle, ring: "border-hold bg-hold-bg", sub: () => "Pay only after the listed documents are received and checked." },
  { v: "WARRANTY_REVIEW", title: "Return Under Warranty", Icon: ShieldQuestion, ring: "border-warranty bg-warranty-bg", sub: (c) => c.warrantySubtitle },
];

export function DecisionPanel({ c, hearing }: { c: CaseDetail; hearing: Hearing | null }) {
  const qc = useQueryClient();
  const [verdict, setVerdict] = useState<Verdict>(c.lead.finalVerdict ?? c.recommendedVerdict);
  const [reason, setReason] = useState("");
  const items = hearing?.evidenceRequired?.length ? hearing.evidenceRequired : c.evidenceRequired;
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  useEffect(() => setChecked({}), [items.join("|")]); // eslint-disable-line react-hooks/exhaustive-deps

  const isOverride = verdict !== c.recommendedVerdict;
  const minLen = isOverride ? 10 : 3;
  const save = useMutation({
    mutationFn: () => api.saveVerdict(c.workOrder.workOrderId, verdict, reason.trim()),
    onSuccess: () => {
      setReason("");
      qc.invalidateQueries({ queryKey: ["case", c.workOrder.workOrderId] });
      qc.invalidateQueries({ queryKey: ["reviews"] });
      qc.invalidateQueries({ queryKey: ["summary"] });
      qc.invalidateQueries({ queryKey: ["receipt", c.workOrder.workOrderId] });
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Decision</CardTitle>
        <CardDescription>
          Rule-based recommendation: <VerdictBadge verdict={c.recommendedVerdict} className="align-middle" /> · {c.verdictPrecedence}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <fieldset>
          <legend className="sr-only">Choose a verdict</legend>
          <div className="grid gap-3 md:grid-cols-3">
            {OPTIONS.map(({ v, title, Icon, ring, sub }) => {
              const active = verdict === v;
              return (
                <label key={v} className={cn("relative flex cursor-pointer flex-col gap-1 rounded-xl border-2 p-4 transition-colors", active ? ring : "border-border hover:bg-muted/50")}>
                  <input type="radio" name="verdict" value={v} checked={active} onChange={() => setVerdict(v)} className="sr-only" />
                  <span className="flex items-center gap-2 font-semibold"><Icon className="size-4" aria-hidden />{title}</span>
                  <span className="text-xs text-muted-foreground">{sub(c)}</span>
                  {v === c.recommendedVerdict && <span className="mt-1 text-[11px] font-medium uppercase tracking-wide">Recommended</span>}
                  {active && <CheckCircle2 className="absolute right-3 top-3 size-4" aria-label="selected" />}
                </label>
              );
            })}
          </div>
        </fieldset>

        <div>
          <div className="mb-2 text-sm font-medium">Evidence request checklist</div>
          {items.length === 0 ? (
            <p className="text-sm text-muted-foreground">No additional evidence required.</p>
          ) : (
            <ul className="space-y-1.5">
              {items.map((it) => (
                <li key={it}>
                  <label className="flex items-start gap-2 text-sm">
                    <input type="checkbox" className="mt-1" checked={!!checked[it]} onChange={(e) => setChecked({ ...checked, [it]: e.target.checked })} />
                    <span className={cn(checked[it] && "text-muted-foreground line-through")}>{it}</span>
                  </label>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="reason">{isOverride ? "Override reason (required, min. 10 characters)" : "Confirmation note (required)"}</Label>
          <Textarea
            id="reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={isOverride ? "Why are you departing from the recommendation? e.g. Geotagged photos show two separate defects 40 m apart." : "e.g. Accept recommendation; evidence requested from ward engineer."}
            maxLength={1000}
          />
          {isOverride && (
            <p className="text-xs text-[oklch(0.45_0.12_60)]">
              You are overriding the recommended {VERDICT_LABEL[c.recommendedVerdict]}. The reason is stored with the decision.
            </p>
          )}
        </div>

        {save.isError && (
          <Alert variant="destructive"><AlertTitle>Could not save</AlertTitle><AlertDescription>{(save.error as Error).message}</AlertDescription></Alert>
        )}
        {save.isSuccess && (
          <Alert variant="info"><CheckCircle2 /><AlertTitle>Decision saved</AlertTitle><AlertDescription>{VERDICT_LABEL[save.data.decision.finalVerdict]} recorded{save.data.decision.isOverride ? " as an override" : ""}.</AlertDescription></Alert>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <Button onClick={() => save.mutate()} disabled={save.isPending || reason.trim().length < minLen}>
            {isOverride ? "Save override" : "Confirm decision"}
          </Button>
          <Button variant="outline" asChild>
            <Link href={`/receipt/${c.workOrder.workOrderId}`}><QrCode />Open Public Receipt</Link>
          </Button>
        </div>

        {c.decisions.length > 0 && (
          <div>
            <div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Decision history</div>
            <ul className="space-y-1 text-sm">
              {[...c.decisions].reverse().map((d) => (
                <li key={d.id} className="flex flex-wrap items-center gap-2">
                  <span className="text-xs text-muted-foreground">{fmtDate(d.createdAt)}</span>
                  <VerdictBadge verdict={d.finalVerdict} />
                  {d.isOverride && <span className="text-xs font-medium">override</span>}
                  <span className="text-muted-foreground">“{d.officerReason}”</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
