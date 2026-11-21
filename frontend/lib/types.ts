// Shared types. The backend returns snake_case JSON; lib/api.ts converts keys to camelCase.
// The backend is the source of truth: the frontend never recalculates audit results.

export type Verdict = "RELEASE_PAYMENT" | "HOLD_FOR_EVIDENCE" | "WARRANTY_REVIEW";

export type ReviewRule = "RATE_CARD_REVIEW" | "POSSIBLE_DUPLICATE" | "DLP_REVIEW" | "LOW_COST_DATA_QUALITY";

export type Confidence = "HIGH" | "MEDIUM" | "LOW";
export type Language = "en" | "mr" | "hi" | "hinglish";
export type ClaudeMode = "live" | "cache" | "template";

export interface ReviewLead {
  workOrderId: string;
  wardCode: string;
  roadId: string;
  roadName: string;
  contractorId: string;
  contractorName: string;
  amountInr: number;
  expectedAmountInr: number;
  rateRatio: number | null;
  rules: ReviewRule[];
  recommendedVerdict: Verdict;
  confidence: Confidence;
  // extra fields returned by the API
  repairMethod: string;
  workType: string;
  completedDate: string;
  rateBand: string;
  isReviewLead: boolean;
  leadCount: number;
  duplicatePartnerId: string | null;
  hasLinkedComplaint: boolean;
  finalVerdict: Verdict | null;
  decisionStatus: "DECIDED" | "AWAITING_OFFICER";
}

export interface Health {
  status: string;
  dataLoaded: boolean;
  claudeMode: ClaudeMode;
  model: string | null;
}

export interface ReviewList {
  total: number;
  limit: number;
  offset: number;
  amountRequiringReviewInr: number;
  items: ReviewLead[];
  filters: {
    wards: string[];
    contractors: { contractorId: string; contractorName: string }[];
    repairMethods: string[];
    rules: ReviewRule[];
    verdicts: Verdict[];
  };
}

export interface WorkOrderFacts {
  workOrderId: string;
  complaintId: string;
  roadId: string;
  roadName: string;
  wardCode: string;
  contractorId: string;
  contractorName: string;
  workType: string;
  repairMethod: string;
  rateCardId: string;
  areaSqm: number;
  costInr: number;
  billedTo: string;
  paymentStatus: string;
  issuedDate: string;
  completedDate: string;
  recordedDate: string;
  slaTier: string;
  slaDays: number;
  slaMet: "Y" | "N";
  reopenedWithin30d: "Y" | "N";
  photoBefore: "Y" | "N";
  photoAfter: "Y" | "N";
  measurementBook: "Y" | "N";
  engineerCertificate: "Y" | "N";
}

export interface Complaint {
  complaintId: string;
  createdAt: string;
  channel: string;
  language: Language;
  textOriginal: string;
  textEn: string;
  category: string;
  upvotes: number;
  status: string;
  duplicateOf: string;
  linkedWorkOrderId: string;
  closedAt: string;
  roadId: string;
  wardCode: string;
  textSuggestsCategory: string | null;
}

export interface RecordConflict {
  type: string;
  sourceIds: string[];
  text: string;
}

export interface TimelineEvent {
  at: string;
  kind: string;
  sourceId: string;
  title: string;
  detail: string;
}

export interface OfficerDecision {
  id: number;
  workOrderId: string;
  recommendedVerdict: Verdict;
  finalVerdict: Verdict;
  isOverride: boolean;
  officerReason: string;
  createdAt: string;
}

export interface DurabilityFeedback {
  id: number;
  workOrderId: string;
  answer: "SURVIVED" | "FAILED" | "UNSURE";
  description: string;
  photoReference: string;
  language: Language;
  createdAt: string;
  generatedWarrantyReview: boolean;
  routedTo: string;
  caseReference: string;
}

export interface CaseDetail {
  lead: ReviewLead;
  workOrder: WorkOrderFacts;
  contractor: { contractorId: string; contractorName: string };
  complaints: Complaint[];
  rateCheck: {
    rateCardId: string;
    unit: string;
    standardRateInr: number;
    areaSqm: number;
    expectedCostInr: number;
    actualCostInr: number;
    rateRatio: number | null;
    rateBand: string;
    bandMeaning: string;
    thresholds: { band: string; label: string; meaning: string }[];
    formula: string;
  };
  duplicate: null | {
    role: "FLAGGED_RECORD" | "EARLIER_RECORD";
    flaggedId: string;
    partnerId: string;
    daysApart: number;
    areaDiffPct: number;
    costDiffPct: number;
    criteria: { label: string; met: boolean; detail?: string }[];
    sameContractor: boolean;
    sideBySide: WorkOrderFacts[];
    label: string;
  };
  dlp: {
    underDlp: boolean;
    dlpStartDate: string | null;
    dlpEndDate: string | null;
    paidByBmc: boolean;
    warrantyOwnerKnown: boolean;
    note: string;
    routing: string | null;
  };
  context: {
    road: { roadId: string; roadName: string; wardCode: string; roadClass: string; bestBusRoute: boolean; busRoutes: number; lowLying: boolean; lat: number; lon: number };
    traffic: { peakHourVehicles: number; congestionIndex: number; busRoutes: number; twoWheelerShare: number; surveyDate: string };
    accidents: { accidentId: string; date: string; severity: string; vehicleType: string; roadConditionRelated: boolean; reportedCause: string; afterCompletion: boolean }[];
    floodHotspots: { hotspotId: string; name: string; distanceM: number; severity: string; tideSensitive: boolean }[];
    rainfall: { date: string; rainfallMm: number }[];
    tideAlerts: { date: string; highTideM: number }[];
    facilitiesNearby: { hospitals: number; schools: number };
    priorityScore: number;
    socialPosts: { postId: string; platform: string; postedAt: string; text: string; linkedComplaintId: string; linkBasis: string }[];
  };
  recordConflicts: RecordConflict[];
  timeline: TimelineEvent[];
  rules: ReviewRule[];
  recommendedVerdict: Verdict;
  verdictPrecedence: string;
  warrantySubtitle: string;
  evidenceRequired: string[];
  evidenceCompleteness: { scorePct: number; present: string[]; missing: string[] };
  confidence: Confidence;
  dataLimitations: string[];
  decisions: OfficerDecision[];
  durabilityFeedback: DurabilityFeedback[];
  sourceIds: string[];
}

export interface Hearing {
  auditorCase: { summary: string; evidence: string[]; sourceIds: string[] };
  fairnessCase: { possibleLegitimateContext: string[]; limitations: string[]; sourceIds: string[] };
  recommendedVerdict: Verdict;
  reasoning: string;
  evidenceRequired: string[];
  citizenExplanation: string;
  officerBrief: string;
  confidence: Confidence;
  mode: ClaudeMode;
  origin: string;
  evidenceHash: string;
  ruleBasedVerdict: Verdict;
  verdictDiffersFromRules: boolean;
  suppliedSourceIds: string[];
  notes: string[];
}

export interface SankeyData {
  nodes: { name: string }[];
  links: { source: number; target: number; value: number }[];
}

export interface Summary {
  cards: {
    uniqueReviewLeads: number;
    amountRequiringReviewInr: number;
    linkageRatePct: number;
    dlpReviewCount: number;
    ruleHits: Record<ReviewRule, number>;
    leadsWithMultipleRules: number;
    dataQualityFlags: number;
    contextBandOrders: number;
    workOrders: number;
    complaints: number;
    decisionsRecorded: number;
  };
  wardSummary: { wardCode: string; wardName: string; overallScore: number; mainSystemIssue: string; uniqueReviewLeads: number }[];
  contractorSummary: {
    contractors: number;
    belowPeersOnDelivery: { contractorId: string; contractorName: string; slaGap: number; durabilityGap: number; sampleSize: number }[];
    dlpLeadsNotAttributed: number;
  };
  sankey: SankeyData;
  map: { leadPoints: LeadPoint[]; priorityPoints: PriorityPoint[] };
  methodology: string[];
}

export interface LeadPoint {
  roadId: string;
  roadName: string;
  wardCode: string;
  lat: number;
  lon: number;
  leads: number;
  amountInr: number;
  workOrderIds: string[];
}
export interface PriorityPoint {
  roadId: string;
  roadName: string;
  wardCode: string;
  lat: number;
  lon: number;
  priorityScore: number;
  underDlp: boolean;
}

export interface PeerGroupScore {
  peerGroup: string;
  repairMethod: string;
  slaTier: string;
  sampleSize: number;
  peerSampleSize: number;
  peerContractors: number;
  confidence: Confidence;
  lowSampleWarning: boolean;
  slaReliability: number | null;
  peerSlaReliability: number | null;
  durability: number | null;
  peerDurability: number | null;
  rateAlignment: number | null;
  peerRateAlignment: number | null;
  evidenceCompleteness: number | null;
  peerEvidenceCompleteness: number | null;
}

export interface ContractorScore {
  contractorId: string;
  contractorName: string;
  sampleSize: number;
  confidence: Confidence;
  overallScore: number;
  dimensions: { slaReliability: number | null; durability: number | null; rateAlignment: number | null; evidenceCompleteness: number | null };
  gapVsPeers: { slaReliability: number | null; durability: number | null; rateAlignment: number | null; evidenceCompleteness: number | null };
  peerGroups: PeerGroupScore[];
  openReviewLeads: { count: number; dlpReviewNotAttributed: number; possibleDuplicatesNotScored: number; rateCardLeads: number };
  evidenceLinks: { slaBreaches: string[]; reopened: string[]; outsideRateRange: string[] };
}

export interface WardScore {
  wardCode: string;
  wardName: string;
  zone: string;
  sampleSize: number;
  confidence: Confidence;
  overallScore: number;
  dimensions: { linkage: number | null; dlpControl: number | null; duplicateControl: number | null; slaOversight: number | null; riskAllocation: number | null };
  metrics: { workOrders: number; billedWorkOrders: number; billedAmountInr: number; dlpRoadWorkOrders: number; duplicateLikeRecords: number; uniqueReviewLeads: number; amountRequiringReviewInr: number };
  attribution: {
    contractorDelivery: { slaBreaches: number; reopenedWithin30d: number; evidenceGaps: number };
    wardSystem: { workOrdersWithoutComplaint: number; dlpRoadPayments: number; dlpRoadPaymentsInr: number; duplicateLikeRecords: number };
    dataQuality: { lowCostOutliers: number; complaintCategoryConflicts: number };
  };
  evidenceLinks: { dlpRoadPayments: string[]; duplicateLike: string[]; missingComplaint: string[]; categoryConflicts: string[] };
}

export interface ScorecardMethodology {
  contractorDimensions: Record<string, string>;
  wardDimensions: Record<string, string>;
  peerGroup: string;
  confidence: string;
  notScoredAgainstContractors: string;
}

export interface PlanItem {
  roadId: string;
  roadName: string;
  roadClass: string;
  priorityScore: number;
  estimatedAreaSqm: number;
  recommendedMethod: string;
  rateCardId: string;
  estimatedCostInr: number;
  lifetimeCost3yInr: number;
  cheapestUpfrontMethod: string;
  cheapestUpfrontCostInr: number;
  cheapestLifetimeCost3yInr: number;
  methodDurability: { reopenRatePct: number; historicalJobs: number; expectedLifeMonths: number; effectiveLifeMonths: number };
  whyPrioritised: string[];
  riskEvidence: Record<string, number | string | string[]>;
  lat: number;
  lon: number;
  remainingAfterInr?: number;
  reasonNotSelected?: string;
}

export interface WarrantyRoute {
  roadId: string;
  roadName: string;
  priorityScore: number;
  estimatedAreaSqm: number;
  newBmcAllocationInr: number;
  action: string;
  countedAsSaving: boolean;
  note: string;
  whyPrioritised: string[];
}

export interface Plan {
  wardCode: string;
  budgetInr: number;
  recoveredInr: number;
  spendableInr: number;
  allocatedInr: number;
  remainingInr: number;
  heldForReviewInWardInr: number;
  heldNote: string;
  selected: PlanItem[];
  warrantyRoutes: WarrantyRoute[];
  notSelected: PlanItem[];
  methodComparison: {
    repairMethod: string;
    rateCardId: string;
    standardRateInr: number;
    expectedLifeMonths: number;
    reopenRate: number;
    effectiveLifeMonths: number;
    lifetimeCostPerSqmYear: number;
    repairsInHorizon: number;
    jobs: number;
  }[];
  weights: Record<string, number>;
  methodology: string;
}

export interface Receipt {
  language: Language;
  labels: Record<string, string>;
  workOrderId: string;
  complaint: null | { complaintId: string; language: Language; textOriginal: string; upvotes: number; createdAt: string };
  complaintSummary: string;
  roadId: string;
  roadName: string;
  wardCode: string;
  contractorName: string;
  contractorId: string;
  repairMethod: string;
  completedDate: string;
  amountInr: number;
  slaMet: boolean;
  reopenedWithin30d: boolean;
  dlp: { underDlp: boolean; dlpEndDate: string | null; text: string };
  verdict: Verdict;
  statusText: string;
  statusSource: string;
  isReviewLead: boolean;
  evidenceCompletenessPct: number;
  sourceIds: string[];
  related: null | { workOrderId: string; relation: string; completedDate: string; amountInr: number; complaintSummary: string; complaintId: string | null };
  feedbackCounts: Record<"SURVIVED" | "FAILED" | "UNSURE", number>;
  warrantyCases: { caseReference: string; createdAt: string; routedTo: string }[];
  qrNote: string;
}

export interface FeedbackResult {
  feedback: DurabilityFeedback;
  message: string;
  caseType: "WARRANTY_REVIEW" | "REPAIR_FAILURE_REPORT" | null;
  photoNote: string | null;
}
