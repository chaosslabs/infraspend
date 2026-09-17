export type ActionStatus =
  | "Proposed"
  | "Accepted"
  | "Testing"
  | "Measured"
  | "Deferred"
  | "Rejected";
export interface Plan {
  name: string;
  month: string;
  budget: number;
  variableCost: number;
  fixedCost: number;
  growth: number;
  reduction: number;
  basis: "Manual estimate" | "Provider-reported" | "Manual bill";
  evidence: string;
  action: {
    title: string;
    owner: string;
    status: ActionStatus;
    criteria: string;
    baselineWindow: string;
    comparisonWindow: string;
    baselineCost: number | null;
    baselineUnits: number | null;
    resultCost: number | null;
    resultUnits: number | null;
    quality: "Not reviewed" | "Passed" | "Failed";
    notes: string;
  };
}
export interface PlanVersion {
  plan_id: string;
  version: number;
  created_at: string;
  payload: Plan;
}
export const emptyPlan = (): Plan => ({
  name: "",
  month: new Date().toISOString().slice(0, 7),
  budget: 0,
  variableCost: 0,
  fixedCost: 0,
  growth: 0,
  reduction: 0,
  basis: "Manual estimate",
  evidence: "",
  action: {
    title: "",
    owner: "",
    status: "Proposed",
    criteria: "",
    baselineWindow: "",
    comparisonWindow: "",
    baselineCost: null,
    baselineUnits: null,
    resultCost: null,
    resultUnits: null,
    quality: "Not reviewed",
    notes: "",
  },
});
export const samplePlan = (): Plan => ({
  ...emptyPlan(),
  name: "Support assistant",
  budget: 1500,
  variableCost: 1000,
  fixedCost: 200,
  growth: 50,
  reduction: 25,
  evidence:
    "Illustrative monthly baseline: API A $700 + API B $300; subscriptions $200. All amounts and assumptions are fictional.",
  action: {
    ...emptyPlan().action,
    title: "Test caching repeated context",
    owner: "Sample platform team",
    criteria:
      "Evaluate 200 representative tasks. Keep acceptance at or above baseline and p95 latency below 2 seconds. The 25% reduction is an assumption, not measured savings.",
  },
});
export const money = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(amount);
export function comparePlan(plan: Plan) {
  const variable = plan.variableCost * (1 + plan.growth / 100);
  const current = variable + plan.fixedCost;
  const proposed = variable * (1 - plan.reduction / 100) + plan.fixedCost;
  return {
    current,
    proposed,
    difference: current - proposed,
    headroom: plan.budget - proposed,
  };
}
export function measuredOutcome(
  plan: Plan
): { before: number; after: number; normalizedDifference: number } | null {
  const a = plan.action;
  if (
    a.baselineCost == null ||
    a.resultCost == null ||
    !a.baselineUnits ||
    !a.resultUnits
  )
    return null;
  const before = a.baselineCost / a.baselineUnits,
    after = a.resultCost / a.resultUnits;
  return {
    before,
    after,
    normalizedDifference: (before - after) * a.resultUnits,
  };
}
export function validatePlan(plan: Plan): string | null {
  if (!plan.name.trim()) return "Name this plan before saving.";
  if (
    !/^\d{4}-(0[1-9]|1[0-2])$/.test(plan.month) ||
    plan.month.startsWith("0000")
  )
    return "Choose a valid planning month.";
  if (
    ![plan.budget, plan.variableCost, plan.fixedCost].every(
      (n) => Number.isFinite(n) && n >= 0 && n <= 1e10
    )
  )
    return "Costs and budget must be between 0 and 10 billion USD.";
  if (
    !Number.isFinite(plan.growth) ||
    plan.growth < -100 ||
    plan.growth > 1000 ||
    !Number.isFinite(plan.reduction) ||
    plan.reduction < 0 ||
    plan.reduction > 100
  )
    return "Growth must be −100% to 1,000%; reduction must be 0% to 100%.";
  if (plan.basis !== "Manual estimate" && !plan.evidence.trim())
    return "Add a source and billing period for this baseline.";
  const a = plan.action;
  if (
    ["Accepted", "Testing", "Measured"].includes(a.status) &&
    (!a.title.trim() || !a.owner.trim() || !a.criteria.trim())
  )
    return "An accepted action needs a title, owner, and success criteria.";
  for (const n of [
    a.baselineCost,
    a.resultCost,
    a.baselineUnits,
    a.resultUnits,
  ])
    if (n != null && (!Number.isFinite(n) || n < 0 || n > 1e10))
      return "Measurements must be finite, nonnegative values up to 10 billion.";
  if (
    a.status === "Measured" &&
    (!measuredOutcome(plan) ||
      !a.baselineWindow.trim() ||
      !a.comparisonWindow.trim() ||
      !a.notes.trim() ||
      a.quality === "Not reviewed")
  )
    return "To mark measured, add both windows, costs, positive accepted-task counts, a quality review, and confounder notes.";
  return null;
}
