"use client";

import dynamic from "next/dynamic";
import { Skeleton } from "@/components/ui/skeleton";

// Leaflet touches `window`, so it is loaded on the client only.
export const RoadMap = dynamic(() => import("./road-map-inner"), {
  ssr: false,
  loading: () => <Skeleton className="h-[380px] w-full" />,
});
export type { MapPoint } from "./road-map-inner";
