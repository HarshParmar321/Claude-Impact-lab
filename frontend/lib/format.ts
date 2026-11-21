import type { Verdict, ReviewRule } from "./types";

const inrFmt = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
export const inr = (v: number | null | undefined) => (v === null || v === undefined ? "—" : inrFmt.format(v));

/** Compact Indian format: ₹2.45 Cr, ₹3.2 L */
export function inrCompact(v: number) {
  if (Math.abs(v) >= 1e7) return `₹${(v / 1e7).toFixed(2)} Cr`;
  if (Math.abs(v) >= 1e5) return `₹${(v / 1e5).toFixed(2)} L`;
  return inr(v);
}

export const num = (v: number | null | undefined) => (v === null || v === undefined ? "—" : new Intl.NumberFormat("en-IN").format(v));
export const pct = (v: number | null | undefined, digits = 1) => (v === null || v === undefined ? "n/a" : `${v.toFixed(digits)}%`);
export const ratio = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${v.toFixed(2)}×`);

export const VERDICT_LABEL: Record<Verdict, string> = {
  RELEASE_PAYMENT: "Release Payment",
  HOLD_FOR_EVIDENCE: "Hold for Evidence",
  WARRANTY_REVIEW: "Warranty Review",
};

export const RULE_LABEL: Record<ReviewRule, string> = {
  DLP_REVIEW: "DLP review",
  POSSIBLE_DUPLICATE: "Possible duplicate",
  RATE_CARD_REVIEW: "Rate-card lead",
  LOW_COST_DATA_QUALITY: "Low-cost data quality",
};

export const humanize = (s: string) => s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export function fmtDate(s: string | null | undefined) {
  if (!s) return "—";
  const d = new Date(s.length === 10 ? `${s}T00:00:00` : s);
  if (Number.isNaN(d.getTime())) return s;
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

/** "dlpControl" → "DLP control", "slaReliability" → "SLA reliability" */
export function camelLabel(k: string) {
  const words = k.replace(/([A-Z])/g, " $1").toLowerCase().split(" ");
  const acr = new Set(["sla", "dlp", "bmc"]);
  const s = words.map((w) => (acr.has(w) ? w.toUpperCase() : w)).join(" ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}
