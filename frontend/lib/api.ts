import type {
  CaseDetail, FeedbackResult, Health, Hearing, Language, OfficerDecision, Plan, Receipt, ReviewList,
  ContractorScore, ScorecardMethodology, Summary, Verdict, WardScore,
} from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api").replace(/\/$/, "");

const SNAKE = /^[a-z][a-z0-9]*(_[a-z0-9]+)+$/;
const toCamel = (k: string) => (SNAKE.test(k) ? k.replace(/_([a-z0-9])/g, (_, c: string) => c.toUpperCase()) : k);

/** Convert snake_case keys to camelCase. Data-valued keys such as "DLP_REVIEW" are left alone. */
export function camelize<T>(value: unknown): T {
  if (Array.isArray(value)) return value.map((v) => camelize(v)) as T;
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([k, v]) => [toCamel(k), camelize(v)])) as T;
  }
  return value as T;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  } catch {
    throw new ApiError(0, `Cannot reach the NagarLens API at ${API_BASE}. Is the backend running on port 8000?`);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {}
    throw new ApiError(res.status, detail);
  }
  return camelize<T>(await res.json());
}

const qs = (params: Record<string, string | number | boolean | undefined | null>) => {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  });
  const s = p.toString();
  return s ? `?${s}` : "";
};

export interface ReviewFilters {
  ward?: string;
  contractor?: string;
  rule?: string;
  verdict?: string;
  repair_method?: string;
  include_data_quality?: boolean;
  q?: string;
  limit?: number;
  offset?: number;
}

export const api = {
  health: () => request<Health>("/health"),
  summary: () => request<Summary>("/summary"),
  reviews: (f: ReviewFilters) => request<ReviewList>(`/reviews${qs({ ...f })}`),
  review: (id: string) => request<CaseDetail>(`/reviews/${encodeURIComponent(id)}`),
  hearing: (id: string, forceTemplate = false) =>
    request<Hearing>(`/reviews/${encodeURIComponent(id)}/hearing${qs({ force_template: forceTemplate || undefined })}`, { method: "POST" }),
  saveVerdict: (id: string, verdict: Verdict, officerReason: string) =>
    request<{ decision: OfficerDecision }>(`/reviews/${encodeURIComponent(id)}/verdict`, {
      method: "PATCH",
      body: JSON.stringify({ verdict, officer_reason: officerReason }),
    }),
  contractors: () => request<{ items: ContractorScore[]; methodology: ScorecardMethodology }>("/scorecards/contractors"),
  wards: () => request<{ items: WardScore[]; methodology: ScorecardMethodology }>("/scorecards/wards"),
  plannerWards: () => request<{ items: { wardCode: string; wardName: string; annualRoadBudgetInr: number }[] }>("/planner/wards"),
  planner: (wardCode: string, budgetInr: number, recoveredInr: number) =>
    request<Plan>(`/planner/recommendations${qs({ ward_code: wardCode, budget_inr: budgetInr, recovered_inr: recoveredInr })}`),
  receipt: (id: string, language: Language) => request<Receipt>(`/receipts/${encodeURIComponent(id)}${qs({ language })}`),
  feedback: (id: string, body: { answer: "SURVIVED" | "FAILED" | "UNSURE"; description: string; language: Language; photo_reference?: string }) =>
    request<FeedbackResult>(`/receipts/${encodeURIComponent(id)}/durability-feedback`, { method: "POST", body: JSON.stringify(body) }),
  ask: (id: string, question: string, language: Language) =>
    request<{ answer: string; language: Language; mode: "live" | "template"; sourceIds: string[] }>(`/receipts/${encodeURIComponent(id)}/ask`, {
      method: "POST",
      body: JSON.stringify({ question, language }),
    }),
};
