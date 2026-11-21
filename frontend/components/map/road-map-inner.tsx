"use client";

import "leaflet/dist/leaflet.css";
import Link from "next/link";
import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip } from "react-leaflet";


export interface MapPoint {
  id: string;
  lat: number;
  lon: number;
  kind: "lead" | "priority" | "selected" | "warranty";
  title: string;
  lines?: string[];
  href?: string;
  weight?: number; // 1..n, controls radius
}

const STYLE = {
  lead: { color: "oklch(0.5 0.17 295)", fill: "oklch(0.6 0.17 295)", label: "Review lead(s)" },
  priority: { color: "oklch(0.5 0.13 60)", fill: "oklch(0.75 0.14 70)", label: "High-priority road" },
  selected: { color: "oklch(0.42 0.11 230)", fill: "oklch(0.55 0.12 230)", label: "Selected for funding" },
  warranty: { color: "oklch(0.5 0.17 295)", fill: "oklch(0.96 0.03 295)", label: "Warranty route (₹0 BMC)" },
} as const;

export default function RoadMapInner({ points, height = 380, center }: { points: MapPoint[]; height?: number; center?: [number, number] }) {
  const c: [number, number] =
    center ?? (points.length ? [points.reduce((s, p) => s + p.lat, 0) / points.length, points.reduce((s, p) => s + p.lon, 0) / points.length] : [19.07, 72.88]);
  const kinds = Array.from(new Set(points.map((p) => p.kind)));
  return (
    <div className="relative overflow-hidden rounded-lg border" style={{ height }}>
      <MapContainer
        key={points.map((p) => p.id).join("|").slice(0, 200)}
        {...(points.length > 1 && !center
          ? { bounds: points.map((p) => [p.lat, p.lon] as [number, number]), boundsOptions: { padding: [30, 30], maxZoom: 15 } }
          : { center: c, zoom: 14 })}
        scrollWheelZoom={false}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {points.map((p) => {
          const s = STYLE[p.kind];
          return (
            <CircleMarker
              key={`${p.kind}-${p.id}`}
              center={[p.lat, p.lon]}
              radius={Math.min(16, 5 + (p.weight ?? 1) * 2)}
              pathOptions={{ color: s.color, fillColor: s.fill, fillOpacity: p.kind === "warranty" ? 0.9 : 0.65, weight: p.kind === "warranty" ? 3 : 1.5, dashArray: p.kind === "priority" ? "3 3" : undefined }}
            >
              <Tooltip>{p.title}</Tooltip>
              <Popup>
                <div className="space-y-1 text-xs">
                  <div className="font-semibold">{p.title}</div>
                  {p.lines?.map((l) => <div key={l}>{l}</div>)}
                  {p.href && (
                    <Link className="text-primary underline" href={p.href}>
                      Open
                    </Link>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
      <div className="pointer-events-none absolute bottom-2 left-2 z-[400] space-y-1 rounded-md border bg-card/95 px-2 py-1.5 text-[11px] shadow-sm">
        {kinds.map((k) => (
          <div key={k} className="flex items-center gap-1.5">
            <span className="inline-block size-2.5 rounded-full border" style={{ background: STYLE[k].fill, borderColor: STYLE[k].color, borderStyle: k === "priority" ? "dashed" : "solid" }} />
            {STYLE[k].label}
          </div>
        ))}
        <div className="text-muted-foreground">Synthetic locations</div>
      </div>
    </div>
  );
}

