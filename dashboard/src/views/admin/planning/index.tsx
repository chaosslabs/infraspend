import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import { CallBackendService } from "utils";
import {
  comparePlan,
  emptyPlan,
  measuredOutcome,
  money,
  Plan,
  PlanVersion,
  samplePlan,
  validatePlan,
} from "./model";

const label = "block text-sm font-medium";
function NumberField({
  name,
  value,
  onChange,
  min = 0,
  max = 1e10,
  nullable = false,
}: {
  name: string;
  value: number | null;
  onChange: (value: number | null) => void;
  min?: number;
  max?: number;
  nullable?: boolean;
}) {
  return (
    <label className={label}>
      {name}
      <input
        className="is-input"
        aria-label={name}
        type="number"
        min={min}
        max={max}
        step="any"
        required={!nullable}
        value={value == null || Number.isNaN(value) ? "" : value}
        onChange={(e) =>
          onChange(
            e.target.value === ""
              ? nullable
                ? null
                : NaN
              : Number(e.target.value)
          )
        }
      />
    </label>
  );
}
function TextField({
  name,
  value,
  onChange,
  long = false,
}: {
  name: string;
  value: string;
  onChange: (v: string) => void;
  long?: boolean;
}) {
  return (
    <label className={label}>
      {name}
      {long ? (
        <textarea
          className="is-input"
          rows={3}
          maxLength={4000}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      ) : (
        <input
          className="is-input"
          maxLength={200}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
    </label>
  );
}
export function PlanningWorkspace({ demo = false }: { demo?: boolean }) {
  const { getAccessTokenSilently } = useAuth0();
  const [plan, setPlan] = useState<Plan>(() =>
    demo ? samplePlan() : emptyPlan()
  );
  const [saved, setSaved] = useState<PlanVersion[]>([]);
  const [selected, setSelected] = useState<PlanVersion | null>(null);
  const [history, setHistory] = useState<PlanVersion[]>([]);
  const [loading, setLoading] = useState(!demo);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [dirty, setDirty] = useState(false);
  const [id, setId] = useState(() => crypto.randomUUID());
  const load = useCallback(async () => {
    if (demo) return;
    setLoading(true);
    setError("");
    try {
      const result: { data: PlanVersion[] } = await CallBackendService(
        "/v1/planning?limit=100",
        getAccessTokenSilently
      );
      setSaved(result.data);
      setSelected(null);
      setPlan(emptyPlan());
      setId(crypto.randomUUID());
      setDirty(false);
      setHistory([]);
      setLoadError(false);
    } catch (e) {
      setLoadError(true);
      setError(e instanceof Error ? e.message : "Unable to load plans.");
    } finally {
      setLoading(false);
    }
  }, [demo, getAccessTokenSilently]);
  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  const edit = <K extends keyof Plan>(key: K, value: Plan[K]) => {
    setPlan((p) => ({ ...p, [key]: value }));
    setDirty(true);
    setNotice("");
  };
  const action = <K extends keyof Plan["action"]>(
    key: K,
    value: Plan["action"][K]
  ) => edit("action", { ...plan.action, [key]: value });
  const choose = (revision: PlanVersion | null) => {
    setSelected(revision);
    setId(revision?.plan_id || crypto.randomUUID());
    setPlan(revision?.payload || (demo ? samplePlan() : emptyPlan()));
    setHistory([]);
    setDirty(false);
    setNotice("");
    setError("");
  };
  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    const invalid = validatePlan(plan);
    if (invalid) {
      setError(invalid);
      return;
    }
    setSaving(true);
    setError("");
    try {
      const result: { data: PlanVersion } = demo
        ? {
            data: {
              plan_id: id,
              version: (selected?.version || 0) + 1,
              created_at: new Date().toISOString(),
              payload: JSON.parse(JSON.stringify(plan)),
            },
          }
        : await CallBackendService("/v1/planning", getAccessTokenSilently, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              plan_id: id,
              expected_version: selected?.version || 0,
              payload: plan,
            }),
          });
      setSelected(result.data);
      setSaved((rows) => [
        result.data,
        ...rows.filter((r) => r.plan_id !== id),
      ]);
      setHistory((rows) => [result.data, ...rows]);
      setDirty(false);
      setNotice(
        demo
          ? "Sample revision saved for this visit only. No account data was changed."
          : `Revision ${result.data.version} saved.`
      );
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Could not save. Your draft is still here."
      );
    } finally {
      setSaving(false);
    }
  };
  const exportPlan = () => {
    const blob = new Blob(
      [
        JSON.stringify(
          {
            kind: demo ? "sample" : "manual-scenario",
            savedRevision: selected?.version || null,
            unsavedChanges: dirty,
            exportedAt: new Date().toISOString(),
            payload: plan,
          },
          null,
          2
        ),
      ],
      { type: "application/json" }
    );
    const url = URL.createObjectURL(blob),
      anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `infraspend-${demo ? "sample" : "plan"}-${
      plan.month
    }.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };
  const comparison = comparePlan(plan);
  const validNumbers = [
    comparison.current,
    comparison.proposed,
    comparison.headroom,
  ].every(Number.isFinite);
  const outcome = measuredOutcome(plan);
  if (loading)
    return (
      <p role="status" className="is-muted">
        Loading plans…
      </p>
    );
  return (
    <div className="space-y-6">
      {demo && (
        <p
          className="rounded-lg bg-amber-100 p-3 text-sm text-amber-900"
          role="status"
        >
          Sample workspace · Fictional costs and assumptions. Changes last only
          for this visit.
        </p>
      )}
      {!demo && (
        <div className="flex flex-wrap items-end gap-3">
          <label className={label}>
            Saved plans
            <select
              className="is-input"
              value={selected?.plan_id || ""}
              disabled={dirty || saving || loadError}
              onChange={(e) =>
                choose(saved.find((r) => r.plan_id === e.target.value) || null)
              }
            >
              <option value="">New plan</option>
              {saved.map((r) => (
                <option key={r.plan_id} value={r.plan_id}>
                  {r.payload.name} · {r.payload.month}
                </option>
              ))}
            </select>
          </label>
          {dirty && (
            <button
              type="button"
              className="is-button-secondary"
              disabled={saving}
              onClick={() => choose(selected)}
            >
              Discard draft changes
            </button>
          )}
          <button
            type="button"
            className="is-button-secondary"
            disabled={dirty || saving}
            onClick={load}
          >
            Reload plans
          </button>
          <span className="is-muted">
            {dirty
              ? "Unsaved changes — save or discard before switching plans."
              : "Up to 100 recent plans. Separate from account budgets."}
          </span>
        </div>
      )}
      <form onSubmit={save}>
        <fieldset disabled={saving || loadError} className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
            <section className="is-panel space-y-5">
              <div className="grid gap-4 sm:grid-cols-2">
                <TextField
                  name="Plan name"
                  value={plan.name}
                  onChange={(v) => edit("name", v)}
                />
                <label className={label}>
                  Planning month
                  <input
                    className="is-input"
                    type="month"
                    required
                    value={plan.month}
                    onChange={(e) => edit("month", e.target.value)}
                  />
                </label>
              </div>
              <NumberField
                name="Monthly budget (USD)"
                value={plan.budget}
                onChange={(v) => edit("budget", v!)}
              />
              <NumberField
                name="Baseline API / usage cost (USD)"
                value={plan.variableCost}
                onChange={(v) => edit("variableCost", v!)}
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <NumberField
                  name="Expected usage change (%)"
                  value={plan.growth}
                  min={-100}
                  max={1000}
                  onChange={(v) => edit("growth", v!)}
                />
                <NumberField
                  name="Reduction to test (%)"
                  value={plan.reduction}
                  max={100}
                  onChange={(v) => edit("reduction", v!)}
                />
              </div>
              <details>
                <summary className="cursor-pointer font-semibold">
                  Fixed costs & assumptions
                </summary>
                <div className="mt-4 space-y-4">
                  <NumberField
                    name="Fixed subscriptions / other costs (USD)"
                    value={plan.fixedCost}
                    onChange={(v) => edit("fixedCost", v!)}
                  />
                  <label className={label}>
                    Baseline source
                    <select
                      className="is-input"
                      value={plan.basis}
                      onChange={(e) =>
                        edit("basis", e.target.value as Plan["basis"])
                      }
                    >
                      {[
                        "Manual estimate",
                        "Provider-reported",
                        "Manual bill",
                      ].map((b) => (
                        <option key={b}>{b}</option>
                      ))}
                    </select>
                  </label>
                  <TextField
                    name="Source, billing period & assumptions"
                    long
                    value={plan.evidence}
                    onChange={(v) => edit("evidence", v)}
                  />
                  <p className="is-muted">
                    All inputs are entered by you. A source label is your
                    attribution, not independent verification. Record provider,
                    account, period, exclusions, and any effective rate changes
                    here. No model prices are assumed.
                  </p>
                </div>
              </details>
            </section>
            <section
              className="is-panel flex flex-col justify-between gap-6"
              aria-label="Plan comparison"
            >
              <div>
                <p className="is-muted">With the proposed change</p>
                <p className="mt-2 text-4xl font-bold">
                  {validNumbers ? money(comparison.proposed) : "—"}
                  <span className="ml-2 text-sm font-normal">/ month</span>
                </p>
                <p className="mt-3 font-medium">
                  {validNumbers
                    ? `${money(Math.abs(comparison.headroom))} ${
                        comparison.headroom >= 0 ? "under" : "over"
                      } budget`
                    : "Complete the inputs to compare."}
                </p>
              </div>
              <dl className="space-y-4 border-y border-gray-200 py-5 dark:border-white/10">
                <div className="flex justify-between gap-4">
                  <dt>Without the change</dt>
                  <dd>{validNumbers ? money(comparison.current) : "—"}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt>Proposed change</dt>
                  <dd>{validNumbers ? money(comparison.proposed) : "—"}</dd>
                </div>
                <div className="flex justify-between gap-4 font-semibold">
                  <dt>Estimated difference</dt>
                  <dd>{validNumbers ? money(comparison.difference) : "—"}</dd>
                </div>
              </dl>
              <p className="is-muted">
                A scenario, not a forecast or verified saving. Usage cost scales
                with your usage assumption; the reduction applies only to that
                cost. Fixed costs stay unchanged. A budget does not cap provider
                spending.
              </p>
            </section>
          </div>
          <details className="is-panel">
            <summary className="cursor-pointer font-semibold">
              Track an action & check the result
            </summary>
            <div className="mt-5 space-y-5">
              <p className="is-muted">
                Record a proposed change. Monthly totals alone do not prove
                which optimization will work.
              </p>
              <div className="grid gap-4 md:grid-cols-2">
                <TextField
                  name="Action to test"
                  value={plan.action.title}
                  onChange={(v) => action("title", v)}
                />
                <TextField
                  name="Owner"
                  value={plan.action.owner}
                  onChange={(v) => action("owner", v)}
                />
              </div>
              <TextField
                name="Success criteria, quality & latency limits"
                long
                value={plan.action.criteria}
                onChange={(v) => action("criteria", v)}
              />
              <label className={label}>
                Action status
                <select
                  className="is-input"
                  value={plan.action.status}
                  onChange={(e) =>
                    action("status", e.target.value as Plan["action"]["status"])
                  }
                >
                  {[
                    "Proposed",
                    "Accepted",
                    "Testing",
                    "Measured",
                    "Deferred",
                    "Rejected",
                  ].map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </label>
              <details>
                <summary className="cursor-pointer font-semibold">
                  Measurement details
                </summary>
                <div className="mt-4 space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <TextField
                      name="Baseline window"
                      value={plan.action.baselineWindow}
                      onChange={(v) => action("baselineWindow", v)}
                    />
                    <TextField
                      name="Comparison window"
                      value={plan.action.comparisonWindow}
                      onChange={(v) => action("comparisonWindow", v)}
                    />
                    <NumberField
                      name="Baseline cost (USD)"
                      nullable
                      value={plan.action.baselineCost}
                      onChange={(v) => action("baselineCost", v)}
                    />
                    <NumberField
                      name="Result cost (USD)"
                      nullable
                      value={plan.action.resultCost}
                      onChange={(v) => action("resultCost", v)}
                    />
                    <NumberField
                      name="Baseline accepted tasks"
                      nullable
                      value={plan.action.baselineUnits}
                      onChange={(v) => action("baselineUnits", v)}
                    />
                    <NumberField
                      name="Result accepted tasks"
                      nullable
                      value={plan.action.resultUnits}
                      onChange={(v) => action("resultUnits", v)}
                    />
                  </div>
                  <label className={label}>
                    Quality review
                    <select
                      className="is-input"
                      value={plan.action.quality}
                      onChange={(e) =>
                        action(
                          "quality",
                          e.target.value as Plan["action"]["quality"]
                        )
                      }
                    >
                      {["Not reviewed", "Passed", "Failed"].map((s) => (
                        <option key={s}>{s}</option>
                      ))}
                    </select>
                  </label>
                  <TextField
                    name="Evidence, task definition & confounding changes"
                    long
                    value={plan.action.notes}
                    onChange={(v) => action("notes", v)}
                  />
                  {outcome && (
                    <p className="is-muted">
                      Observed cost per accepted task: {money(outcome.before)} →{" "}
                      {money(outcome.after)}. Difference at comparison volume:{" "}
                      {money(outcome.normalizedDifference)}. Quality:{" "}
                      {plan.action.quality}. This comparison does not establish
                      causal savings.
                    </p>
                  )}
                </div>
              </details>
            </div>
          </details>
          <div className="flex flex-wrap items-center gap-3">
            <button type="submit" className="is-button">
              {saving ? "Saving…" : demo ? "Save sample revision" : "Save plan"}
            </button>
            <button
              type="button"
              className="is-button-secondary"
              onClick={exportPlan}
            >
              Export plan
            </button>
            <span className="is-muted">
              {selected ? `Revision ${selected.version}` : "New draft"}
              {dirty ? " · Unsaved changes" : ""}
            </span>
          </div>
        </fieldset>
      </form>
      {error && (
        <p
          role="alert"
          className="rounded-lg bg-red-100 p-3 text-sm text-red-900"
        >
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="is-muted">
          {notice}
        </p>
      )}
      {selected && (
        <details className="is-panel">
          <summary className="cursor-pointer font-semibold">
            Saved revisions
          </summary>
          {!demo && (
            <button
              className="is-button-secondary mt-3"
              onClick={async () => {
                try {
                  const result: { data: PlanVersion[] } =
                    await CallBackendService(
                      `/v1/planning/${selected.plan_id}/history?limit=100`,
                      getAccessTokenSilently
                    );
                  setHistory(result.data);
                } catch (e) {
                  setError(
                    e instanceof Error ? e.message : "Could not load history."
                  );
                }
              }}
            >
              Load revision history
            </button>
          )}
          <p className="is-muted mt-3">
            Up to 100 most recent revisions. Each save preserves its inputs and
            action record.
          </p>
          {history.map((r) => (
            <details key={r.version} className="mt-3">
              <summary className="cursor-pointer text-sm">
                Revision {r.version} · {new Date(r.created_at).toLocaleString()}{" "}
                · {r.payload.action.status}
              </summary>
              <pre className="mt-2 overflow-auto whitespace-pre-wrap break-words text-xs">
                {JSON.stringify(r.payload, null, 2)}
              </pre>
            </details>
          ))}
        </details>
      )}
    </div>
  );
}
export default function Planning() {
  const { user } = useAuth0();
  useEffect(() => {
    document.title = "Plan · InfraSpend";
  }, []);
  return (
    <div className="is-page">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="is-title">Plan your spend</h1>
          <p className="is-muted mt-2">
            Compare one change with your monthly budget.
          </p>
        </div>
        <Link className="is-button-secondary" to="/demo">
          Try a sample
        </Link>
      </header>
      <PlanningWorkspace key={user?.sub || "session"} />
    </div>
  );
}
