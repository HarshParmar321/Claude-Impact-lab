import { BadgeCheck, CircleDashed, PauseCircle, ShieldQuestion, Copy, IndianRupee, Gauge } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { RULE_LABEL, VERDICT_LABEL } from "@/lib/format";
import type { Confidence, ReviewRule, Verdict } from "@/lib/types";
import { cn } from "@/lib/utils";

const VERDICT_STYLE: Record<Verdict, { variant: "release" | "hold" | "warranty"; Icon: typeof BadgeCheck }> = {
  RELEASE_PAYMENT: { variant: "release", Icon: BadgeCheck },
  HOLD_FOR_EVIDENCE: { variant: "hold", Icon: PauseCircle },
  WARRANTY_REVIEW: { variant: "warranty", Icon: ShieldQuestion },
};

export function VerdictBadge({ verdict, className }: { verdict: Verdict; className?: string }) {
  const { variant, Icon } = VERDICT_STYLE[verdict];
  return (
    <Badge variant={variant} className={className}>
      <Icon aria-hidden />
      {VERDICT_LABEL[verdict]}
    </Badge>
  );
}

const RULE_ICON: Record<ReviewRule, typeof Copy> = {
  DLP_REVIEW: ShieldQuestion,
  POSSIBLE_DUPLICATE: Copy,
  RATE_CARD_REVIEW: IndianRupee,
  LOW_COST_DATA_QUALITY: CircleDashed,
};

export function RuleBadge({ rule }: { rule: ReviewRule }) {
  const Icon = RULE_ICON[rule];
  return (
    <Badge variant="outline" className="bg-card font-normal">
      <Icon aria-hidden />
      {RULE_LABEL[rule]}
    </Badge>
  );
}

export function ConfidenceBadge({ confidence, label = "evidence" }: { confidence: Confidence; label?: string }) {
  const bars = confidence === "HIGH" ? 3 : confidence === "MEDIUM" ? 2 : 1;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs" title={`${confidence} ${label} confidence`}>
      <Gauge className="size-3.5 text-muted-foreground" aria-hidden />
      <span className="flex items-end gap-0.5" aria-hidden>
        {[1, 2, 3].map((b) => (
          <span key={b} className={cn("w-1 rounded-sm", b <= bars ? "bg-foreground/70" : "bg-border")} style={{ height: 4 + b * 3 }} />
        ))}
      </span>
      <span>{confidence.charAt(0) + confidence.slice(1).toLowerCase()}</span>
    </span>
  );
}

export function SourceId({ id, className }: { id: string; className?: string }) {
  return <code className={cn("rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground", className)}>{id}</code>;
}

export function SourceList({ ids, label = "Sources" }: { ids: string[]; label?: string }) {
  if (!ids.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
      <span className="mr-1">{label}:</span>
      {ids.map((i) => (
        <SourceId key={i} id={i} />
      ))}
    </div>
  );
}

export function YesNo({ value, yes = "Yes", no = "No", good = "yes" }: { value: boolean; yes?: string; no?: string; good?: "yes" | "no" }) {
  const isGood = good === "yes" ? value : !value;
  return (
    <span className={cn("inline-flex items-center gap-1 font-medium", isGood ? "text-release" : "text-[oklch(0.45_0.12_60)]")}>
      <span aria-hidden>{isGood ? "✓" : "!"}</span>
      {value ? yes : no}
    </span>
  );
}
