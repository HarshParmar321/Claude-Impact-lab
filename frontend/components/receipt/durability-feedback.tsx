"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, HelpCircle, ThumbsDown, ThumbsUp } from "lucide-react";
import { api } from "@/lib/api";
import type { Language, Receipt } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export function DurabilityFeedbackForm({ r, language }: { r: Receipt; language: Language }) {
  const L = r.labels;
  const qc = useQueryClient();
  const [failed, setFailed] = useState(false);
  const [description, setDescription] = useState("");
  const [photo, setPhoto] = useState("");
  const m = useMutation({
    mutationFn: (answer: "SURVIVED" | "FAILED" | "UNSURE") =>
      api.feedback(r.workOrderId, { answer, description, language, photo_reference: photo || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["receipt", r.workOrderId] });
      qc.invalidateQueries({ queryKey: ["case", r.workOrderId] });
    },
  });

  if (m.isSuccess) {
    const d = m.data;
    return (
      <Alert variant={d.caseType === "WARRANTY_REVIEW" ? "warranty" : "info"}>
        <CheckCircle2 />
        <AlertTitle>{d.feedback.caseReference || "✓"}</AlertTitle>
        <AlertDescription>
          <p>{d.message}</p>
          {d.photoNote && <p className="text-xs">{d.photoNote}</p>}
          <Button variant="link" className="h-auto p-0" onClick={() => { m.reset(); setFailed(false); setDescription(""); setPhoto(""); }}>
            ← {L.surviveQ}
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-3">
      <div className="grid gap-2">
        <Button variant="outline" size="lg" className="justify-start border-release/40" onClick={() => m.mutate("SURVIVED")} disabled={m.isPending}>
          <ThumbsUp className="text-release" />{L.survived}
        </Button>
        <Button variant="outline" size="lg" className={`justify-start border-hold/50 ${failed ? "bg-hold-bg" : ""}`} onClick={() => setFailed(true)} disabled={m.isPending} aria-expanded={failed}>
          <ThumbsDown className="text-[oklch(0.45_0.12_60)]" />{L.failed}
        </Button>
        <Button variant="outline" size="lg" className="justify-start" onClick={() => m.mutate("UNSURE")} disabled={m.isPending}>
          <HelpCircle />{L.unsure}
        </Button>
      </div>
      {failed && (
        <div className="space-y-2 rounded-xl border bg-card p-3">
          <label className="text-sm font-medium" htmlFor="desc">{L.describe}</label>
          <Textarea id="desc" value={description} onChange={(e) => setDescription(e.target.value)} maxLength={1000} />
          <label className="text-xs text-muted-foreground" htmlFor="photo">{L.photo}</label>
          <Input id="photo" value={photo} onChange={(e) => setPhoto(e.target.value)} placeholder="demo-photo-001.jpg" maxLength={200} />
          <Button className="w-full" onClick={() => m.mutate("FAILED")} disabled={m.isPending || description.trim().length < 3}>
            {L.submit}
          </Button>
        </div>
      )}
      {m.isError && <p className="text-sm text-destructive">{(m.error as Error).message}</p>}
    </div>
  );
}
