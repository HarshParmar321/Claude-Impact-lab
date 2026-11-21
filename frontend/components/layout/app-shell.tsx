"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ScanSearch } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/reviews", label: "Reviews" },
  { href: "/scorecards", label: "Scorecards" },
  { href: "/planner", label: "Planner" },
];

const MODE_TEXT = {
  live: "Claude: live",
  cache: "Claude: cached",
  template: "Claude: template fallback",
} as const;

export function ClaudeModeIndicator() {
  const { data, isError } = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 30_000 });
  if (isError) return <span className="rounded-md border border-destructive/40 bg-card px-2 py-1 text-xs text-destructive">API offline</span>;
  if (!data) return null;
  return (
    <span
      title={data.claudeMode === "live" ? `Model: ${data.model}` : "No API key: Fair Hearings use committed cached responses, else a deterministic template."}
      className="rounded-md border bg-card px-2 py-1 text-xs text-muted-foreground"
    >
      <span className={cn("mr-1.5 inline-block size-2 rounded-full", data.claudeMode === "live" ? "bg-release" : data.claudeMode === "cache" ? "bg-primary" : "bg-hold")} />
      {MODE_TEXT[data.claudeMode]}
    </span>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isReceipt = pathname.startsWith("/receipt");

  if (isReceipt) {
    return (
      <div className="min-h-screen">
        <header className="border-b bg-card">
          <div className="mx-auto flex h-12 max-w-lg items-center gap-2 px-4">
            <ScanSearch className="size-5 text-primary" aria-hidden />
            <span className="font-semibold">NagarLens</span>
            <span className="text-xs text-muted-foreground">· Public Repair Receipt</span>
          </div>
        </header>
        <main className="mx-auto max-w-lg px-4 py-5">{children}</main>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b bg-card/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2">
            <ScanSearch className="size-5 text-primary" aria-hidden />
            <span className="font-semibold tracking-tight">NagarLens</span>
            <span className="hidden text-xs text-muted-foreground lg:inline">RupeeProof Action Layer</span>
          </Link>
          <nav className="flex items-center gap-1" aria-label="Primary">
            {NAV.map((n) => {
              const active = n.href === "/" ? pathname === "/" : pathname.startsWith(n.href);
              return (
                <Link
                  key={n.href}
                  href={n.href}
                  aria-current={active ? "page" : undefined}
                  className={cn("rounded-md px-3 py-1.5 text-sm font-medium transition-colors", active ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground")}
                >
                  {n.label}
                </Link>
              );
            })}
          </nav>
          <div className="ml-auto">
            <ClaudeModeIndicator />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">{children}</main>
      <footer className="mx-auto max-w-7xl px-4 pb-8 text-xs text-muted-foreground sm:px-6">
        Find the evidence. Hear both sides. Act on every rupee. · Synthetic demonstration dataset · Flags are review leads, not findings of wrongdoing.
      </footer>
    </div>
  );
}
