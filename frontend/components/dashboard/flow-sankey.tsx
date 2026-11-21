"use client";

import { ResponsiveContainer, Sankey, Tooltip } from "recharts";
import type { SankeyData } from "@/lib/types";

const NODE_COLOR: Record<string, string> = {
  "Release Payment": "oklch(0.52 0.13 155)",
  "Hold for Evidence": "oklch(0.68 0.15 70)",
  "Warranty Review": "oklch(0.5 0.17 295)",
  "Work orders without complaint": "oklch(0.6 0.03 257)",
  "No work order": "oklch(0.7 0.02 257)",
  "Closed as duplicate": "oklch(0.7 0.02 257)",
};

const SHORT: Record<string, string> = {
  "Citizen complaints": "Complaints",
  "Linked to work order": "Linked to WO",
  "Closed as duplicate": "Closed duplicate",
  "No work order": "No WO yet",
  "Work orders without complaint": "WOs w/o complaint",
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function Node(props: any) {
  const { x, y, width, height, payload } = props;
  const name: string = payload.name;
  const color = NODE_COLOR[name] ?? "oklch(0.42 0.11 230)";
  const cy = y + height / 2;
  return (
    <g>
      <title>{`${name}: ${payload.value}`}</title>
      <rect x={x} y={y} width={width} height={height} fill={color} rx={2} />
      <text x={x + width + 5} y={cy - 2} fontSize={11} fontWeight={500} fill="oklch(0.27 0.03 265)">
        {SHORT[name] ?? name}
      </text>
      <text x={x + width + 5} y={cy + 10} fontSize={10} fill="oklch(0.5 0.025 257)">
        {new Intl.NumberFormat("en-IN").format(payload.value)}
      </text>
    </g>
  );
}

export function FlowSankey({ data }: { data: SankeyData }) {
  return (
    <div className="h-[360px] w-full" role="img" aria-label="Flow from citizen complaints through issue type and work-order linkage to payment verdicts">
      <ResponsiveContainer width="100%" height="100%">
        <Sankey
          data={data}
          node={<Node />}
          nodePadding={22}
          nodeWidth={10}
          margin={{ top: 10, right: 110, bottom: 10, left: 10 }}
          link={{ stroke: "oklch(0.55 0.08 240)", strokeOpacity: 0.18 }}
          iterations={64}
        >
          <Tooltip />
        </Sankey>
      </ResponsiveContainer>
    </div>
  );
}
