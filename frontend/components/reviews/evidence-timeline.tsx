import { AlertTriangle, CarFront, FileText, Hammer, MessageSquare, Megaphone, XCircle } from "lucide-react";
import { fmtDate } from "@/lib/format";
import type { TimelineEvent } from "@/lib/types";
import { SourceId } from "@/components/layout/badges";
import { cn } from "@/lib/utils";

const ICON: Record<string, typeof FileText> = {
  complaint: MessageSquare,
  complaint_closed: XCircle,
  work_order_issued: FileText,
  work_order_completed: Hammer,
  accident: CarFront,
  social: Megaphone,
};

export function EvidenceTimeline({ events, focusId }: { events: TimelineEvent[]; focusId: string }) {
  return (
    <ol className="relative space-y-3 border-l pl-5" aria-label="Complaint-to-payment evidence timeline">
      {events.map((e, i) => {
        const Icon = ICON[e.kind] ?? AlertTriangle;
        const focus = e.sourceId === focusId;
        return (
          <li key={`${e.sourceId}-${e.kind}-${i}`} className="relative">
            <span className={cn("absolute -left-[29px] top-0.5 flex size-6 items-center justify-center rounded-full border bg-card", focus && "border-primary text-primary", e.kind === "accident" && "text-[oklch(0.45_0.12_60)]")}>
              <Icon className="size-3.5" aria-hidden />
            </span>
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
              <span className="text-xs tabular-nums text-muted-foreground">{fmtDate(e.at)}</span>
              <span className={cn("text-sm font-medium", focus && "text-primary")}>{e.title}</span>
              <SourceId id={e.sourceId} />
            </div>
            <p className="mt-0.5 text-sm text-muted-foreground">{e.detail}</p>
          </li>
        );
      })}
    </ol>
  );
}
