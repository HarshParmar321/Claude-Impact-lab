"use client";

import { Suspense } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ErrorState, LoadingBlock, PageHeader } from "@/components/layout/states";
import { ContractorTable } from "@/components/scorecards/contractor-table";
import { WardCards } from "@/components/scorecards/ward-cards";

function Scorecards() {
  const sp = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const tab = sp.get("tab") === "wards" ? "wards" : "contractors";
  const contractors = useQuery({ queryKey: ["scorecards", "contractors"], queryFn: api.contractors });
  const wards = useQuery({ queryKey: ["scorecards", "wards"], queryFn: api.wards });

  return (
    <div>
      <PageHeader
        title="Scorecards"
        description="Explainable, peer-fair comparisons. Contractors are compared only with others using the same repair method in the same SLA tier; wards are scored on process controls with system failures shown separately from contractor delivery."
      />
      <Tabs value={tab} onValueChange={(v) => router.replace(`${pathname}?tab=${v}`, { scroll: false })}>
        <TabsList>
          <TabsTrigger value="contractors">Contractors</TabsTrigger>
          <TabsTrigger value="wards">Wards</TabsTrigger>
        </TabsList>
        <TabsContent value="contractors">
          {contractors.isLoading ? <LoadingBlock rows={6} /> : contractors.error || !contractors.data ? (
            <ErrorState error={contractors.error} onRetry={() => contractors.refetch()} />
          ) : (
            <ContractorTable items={contractors.data.items} methodology={contractors.data.methodology} initial={sp.get("contractor") ?? undefined} />
          )}
        </TabsContent>
        <TabsContent value="wards">
          {wards.isLoading ? <LoadingBlock rows={6} /> : wards.error || !wards.data ? (
            <ErrorState error={wards.error} onRetry={() => wards.refetch()} />
          ) : (
            <WardCards items={wards.data.items} methodology={wards.data.methodology} highlight={sp.get("ward") ?? undefined} />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default function ScorecardsPage() {
  return (
    <Suspense fallback={<LoadingBlock rows={6} />}>
      <Scorecards />
    </Suspense>
  );
}
