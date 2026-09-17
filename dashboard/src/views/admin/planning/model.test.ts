import {
  comparePlan,
  measuredOutcome,
  samplePlan,
  validatePlan,
} from "./model";
test("scales usage, not fixed costs, and compares against a budget", () => {
  const p = samplePlan();
  expect(comparePlan(p)).toEqual({
    current: 1700,
    proposed: 1325,
    difference: 375,
    headroom: 175,
  });
  p.reduction = 100;
  expect(comparePlan(p).proposed).toBe(200);
  p.growth = -100;
  expect(comparePlan(p).proposed).toBe(200);
});
test("rejects invalid numeric inputs instead of showing zero", () => {
  const p = samplePlan();
  p.variableCost = NaN;
  expect(validatePlan(p)).toMatch(/Costs/);
  p.variableCost = 100;
  p.growth = -101;
  expect(validatePlan(p)).toMatch(/Growth/);
});
test("requires evidence for reported baselines and owned actions", () => {
  const p = samplePlan();
  p.basis = "Provider-reported";
  p.evidence = "";
  expect(validatePlan(p)).toMatch(/source/);
  p.evidence = "API A bill, August 2026";
  p.action.status = "Testing";
  p.action.owner = "";
  expect(validatePlan(p)).toMatch(/owner/);
});
test("normalizes observed change by accepted outcomes and rejects incomplete measurements", () => {
  const p = samplePlan();
  p.action.status = "Measured";
  expect(validatePlan(p)).toMatch(/both windows/);
  Object.assign(p.action, {
    baselineCost: 100,
    baselineUnits: 100,
    resultCost: 150,
    resultUnits: 200,
    baselineWindow: "August",
    comparisonWindow: "September",
    quality: "Failed",
    notes: "Different task mix; quality declined",
  });
  expect(measuredOutcome(p)).toEqual({
    before: 1,
    after: 0.75,
    normalizedDifference: 50,
  });
  expect(validatePlan(p)).toBeNull(); // Failed quality may be measured; it is not a successful optimization.
  p.action.resultUnits = 0;
  expect(measuredOutcome(p)).toBeNull();
  expect(validatePlan(p)).not.toBeNull();
});
