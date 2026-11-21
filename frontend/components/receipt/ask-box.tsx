"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Loader2, Send } from "lucide-react";
import { api } from "@/lib/api";
import type { Language } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const PLACEHOLDER: Record<Language, string> = {
  en: "What happened to my complaint?",
  mr: "माझ्या तक्रारीचे काय झाले?",
  hi: "मेरी शिकायत का क्या हुआ?",
  hinglish: "Meri complaint ka kya hua?",
};

export function AskBox({ workOrderId, language, label }: { workOrderId: string; language: Language; label: string }) {
  const [q, setQ] = useState("");
  const m = useMutation({ mutationFn: () => api.ask(workOrderId, q || PLACEHOLDER[language], language) });
  return (
    <div className="space-y-2">
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          m.mutate();
        }}
      >
        <Input aria-label={label} value={q} onChange={(e) => setQ(e.target.value)} placeholder={PLACEHOLDER[language]} />
        <Button type="submit" size="icon" disabled={m.isPending} aria-label="Ask">
          {m.isPending ? <Loader2 className="animate-spin" /> : <Send />}
        </Button>
      </form>
      {m.data && (
        <div className="rounded-lg bg-muted/60 p-3 text-sm">
          {m.data.answer}
          <div className="mt-1 text-[11px] text-muted-foreground">{m.data.mode === "live" ? "Answered by Claude from receipt facts" : "Answered from receipt facts (template)"}</div>
        </div>
      )}
      {m.isError && <p className="text-sm text-destructive">{(m.error as Error).message}</p>}
    </div>
  );
}
