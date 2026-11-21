import { Languages, ThumbsUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { fmtDate, humanize } from "@/lib/format";
import type { Complaint } from "@/lib/types";
import { SourceId } from "@/components/layout/badges";

const LANG: Record<string, string> = { en: "English", mr: "Marathi", hi: "Hindi", hinglish: "Hinglish" };

export function ComplaintList({ complaints }: { complaints: Complaint[] }) {
  if (!complaints.length) return <p className="text-sm text-muted-foreground">No complaints on this road in the review window.</p>;
  return (
    <div className="space-y-3">
      {complaints.map((c) => {
        const conflict = c.textSuggestsCategory && c.textSuggestsCategory !== c.category;
        return (
          <div key={c.complaintId} className="rounded-lg border p-3">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <SourceId id={c.complaintId} />
              <Badge variant="secondary"><Languages aria-hidden />{LANG[c.language] ?? c.language}</Badge>
              <span className="text-muted-foreground">{fmtDate(c.createdAt)} · {c.channel}</span>
              <span className="inline-flex items-center gap-1 text-muted-foreground"><ThumbsUp className="size-3" aria-hidden />{c.upvotes}</span>
              <Badge variant="outline">{humanize(c.status)}{c.duplicateOf ? ` of ${c.duplicateOf}` : ""}</Badge>
            </div>
            <p className="mt-2 text-sm" lang={c.language === "mr" ? "mr" : c.language === "hi" ? "hi" : "en"}>{c.textOriginal}</p>
            {c.language !== "en" && <p className="mt-1 text-sm text-muted-foreground"><span className="font-medium">English:</span> {c.textEn}</p>}
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
              <span className="text-muted-foreground">Category recorded: <span className="font-medium text-foreground">{humanize(c.category)}</span></span>
              {conflict && (
                <Badge variant="hold">Text describes: {humanize(c.textSuggestsCategory!)} — record conflict</Badge>
              )}
              {c.linkedWorkOrderId && <span className="text-muted-foreground">Linked work order: <SourceId id={c.linkedWorkOrderId} /></span>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
