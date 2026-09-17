import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import { CallBackendService } from "utils";
import { useAPIConfigurations } from "./components/hooks/useAPIConfigurations";
import {
  SourceHealthBadge,
  SourceHealthFields,
  deriveSourceHealth,
} from "./components/SourceHealth";
import { BudgetPlan } from "../vendors/hooks/useBudgetPlans";
import { money } from "../planning/model";

const names: Record<string, string> = {
  openai: "OpenAI API",
  anthropic: "Claude API",
  claude: "Claude subscription",
  chatgpt: "ChatGPT subscription",
  aws: "AWS",
  datadog: "Datadog",
  heroku: "Heroku",
};
interface Metric {
  month: string;
  cost: number;
  currency?: string;
  period_start?: string;
  period_end?: string;
}
interface Metrics extends SourceHealthFields {
  data: Metric[];
}
interface Forecast {
  forecast: {
    month: string;
    cost: number;
    best_case: number;
    worst_case: number;
  }[];
  basis?: { message: string };
}
interface Account {
  id: number;
  type: string;
  identifier: string;
}
interface Loaded {
  config: Account;
  metrics: Metrics | null;
  forecast: Forecast | null;
  budgets: BudgetPlan[] | null;
}
const category = (type: string) =>
  ["claude", "chatgpt"].includes(type)
    ? "Manual subscriptions"
    : ["openai", "anthropic"].includes(type)
    ? "AI APIs"
    : "Cloud & other tools";
export default function Dashboard() {
  const { configurations, loading, error, refresh } = useAPIConfigurations();
  const { getAccessTokenSilently } = useAuth0();
  const [rows, setRows] = useState<Loaded[]>([]);
  const [fetching, setFetching] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));
  const monthKey = month ? `${month.slice(5)}-${month.slice(0, 4)}` : "";
  useEffect(() => {
    document.title = "Overview · InfraSpend";
  }, []);
  useEffect(() => {
    let active = true;
    const configs = configurations.filter((c) => names[c.type]);
    if (!configs.length) {
      setRows([]);
      setFetching(false);
      return;
    }
    setFetching(true);
    setRows([]);
    Promise.all(
      configs.map(async (config) => {
        const suffix = `${config.type}?identifier=${encodeURIComponent(
          config.identifier
        )}`;
        // Forecast reads share the same ingestion path. Finish the metrics read
        // first so a cold account does not start two provider imports at once.
        const metricsRequest = CallBackendService(
          `/v1/vendors-metrics/${suffix}`,
          getAccessTokenSilently
        );
        const [m, f, b] = await Promise.allSettled([
          metricsRequest,
          metricsRequest.then(() =>
            CallBackendService(
              `/v1/vendors-forecast/${suffix}`,
              getAccessTokenSilently
            )
          ),
          CallBackendService(
            `/v1/budget-plans?vendor=${config.type}`,
            getAccessTokenSilently
          ),
        ]);
        return {
          config,
          metrics: m.status === "fulfilled" ? (m.value as Metrics) : null,
          forecast: f.status === "fulfilled" ? (f.value as Forecast) : null,
          budgets:
            b.status === "fulfilled" ? (b.value.data as BudgetPlan[]) : null,
        };
      })
    ).then((result) => {
      if (active) {
        setRows(result);
        setFetching(false);
      }
    });
    return () => {
      active = false;
    };
  }, [configurations, getAccessTokenSilently, attempt]);
  if (loading)
    return (
      <div className="is-page" role="status">
        Loading workspace…
      </div>
    );
  if (error)
    return (
      <div className="is-page" role="alert">
        <h1 className="is-title">Could not load your sources</h1>
        <p>{error}</p>
        <button className="is-button" onClick={refresh}>
          Retry
        </button>
      </div>
    );
  if (!configurations.filter((c) => names[c.type]).length)
    return (
      <div className="is-page">
        <section className="is-panel mx-auto max-w-3xl py-10 md:p-10">
          <h1 className="is-title">Plan your AI and engineering spend.</h1>
          <p className="is-muted mt-4 max-w-xl">
            See your costs, compare plans, and understand what could put you
            over budget.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link className="is-button" to="/admin/linked-accounts">
              Add a source
            </Link>
            <Link className="is-button-secondary" to="/demo">
              Try a sample
            </Link>
          </div>
          <p className="is-muted mt-6">
            No credentials yet?{" "}
            <Link className="font-semibold underline" to="/admin/plan">
              Start a manual plan
            </Link>
            .
          </p>
        </section>
      </div>
    );
  return (
    <div className="is-page">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="is-title">Your spend</h1>
          <p className="is-muted mt-2">
            Review costs and budgets, then decide what to change.
          </p>
        </div>
        <Link className="is-button" to="/admin/plan">
          Plan a change
        </Link>
      </header>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm font-medium">
          Month
          <input
            className="is-input"
            type="month"
            required
            value={month}
            onChange={(e) => setMonth(e.target.value)}
          />
        </label>
        <button
          className="is-button-secondary"
          disabled={fetching}
          onClick={() => setAttempt((a) => a + 1)}
        >
          {fetching ? "Loading…" : "Reload"}
        </button>
      </div>
      {fetching ? (
        <p role="status" className="is-muted">
          Loading costs, forecasts and budgets…
        </p>
      ) : (
        ["AI APIs", "Manual subscriptions", "Cloud & other tools"].map(
          (group) => {
            const grouped = rows.filter(
              (r) => category(r.config.type) === group
            );
            if (!grouped.length) return null;
            return (
              <section key={group} className="is-panel">
                <h2 className="mb-4 text-lg font-semibold">{group}</h2>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[680px] text-left text-sm">
                    <thead className="is-muted">
                      <tr>
                        <th className="pb-3">Account</th>
                        <th className="pb-3">Recorded</th>
                        <th className="pb-3">Budget</th>
                        <th className="pb-3">Trend estimate</th>
                        <th className="pb-3">Budget gap</th>
                      </tr>
                    </thead>
                    <tbody>
                      {grouped.map(({ config, metrics, forecast, budgets }) => {
                        const record = metrics?.data?.find(
                          (r) => r.month === monthKey
                        );
                        const cost =
                          record &&
                          (!record.currency || record.currency === "USD")
                            ? record.cost
                            : null;
                        const budget = budgets
                          ?.find((b) => b.identifier === config.identifier)
                          ?.budgets.budgets.find(
                            (b) => b.month === monthKey
                          )?.amount;
                        const estimate = forecast?.forecast?.find(
                          (f) => f.month === monthKey
                        );
                        const gap =
                          budget != null && estimate
                            ? estimate.cost - budget
                            : null;
                        return (
                          <tr
                            key={`${config.type}-${config.id}`}
                            className="border-t border-gray-200 align-top dark:border-white/10"
                          >
                            <td className="py-4 pr-4">
                              <Link
                                className="font-semibold underline"
                                to={`/admin/vendors/${
                                  config.type
                                }?identifier=${encodeURIComponent(
                                  config.identifier
                                )}`}
                              >
                                {names[config.type]}
                              </Link>
                              <p className="is-muted">{config.identifier}</p>
                              {metrics && (
                                <SourceHealthBadge
                                  health={deriveSourceHealth(metrics)}
                                />
                              )}
                              <p className="is-muted mt-1">
                                {group === "Manual subscriptions"
                                  ? "Manually entered"
                                  : "Provider-reported"}
                              </p>
                            </td>
                            <td className="py-4 pr-4">
                              {cost == null ? "Unknown" : money(cost)}
                              <p className="is-muted">
                                {record?.period_start && record.period_end
                                  ? `${record.period_start} to ${record.period_end} (end exclusive)`
                                  : cost == null
                                  ? "No usable record"
                                  : "Period coverage not supplied"}
                              </p>
                            </td>
                            <td className="py-4 pr-4">
                              {budget != null
                                ? money(budget)
                                : budgets
                                ? "Not set"
                                : "Unavailable"}
                            </td>
                            <td className="py-4 pr-4">
                              {estimate ? money(estimate.cost) : "Unavailable"}
                              {estimate && (
                                <p className="is-muted">
                                  {money(estimate.best_case)}–
                                  {money(estimate.worst_case)}
                                  <br />
                                  Growth scenarios
                                </p>
                              )}
                            </td>
                            <td className="py-4">
                              {gap == null
                                ? "—"
                                : `${money(Math.abs(gap))} ${
                                    gap > 0 ? "over" : "under"
                                  }`}
                              <p className="is-muted">
                                {gap == null
                                  ? "Needs a budget and estimate"
                                  : "Based on trend estimate"}
                              </p>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </section>
            );
          }
        )
      )}
      <p className="is-muted">
        Only configured sources are shown. Unknown, unavailable, and missing
        periods are not zero spend. Trend estimates use completed months; growth
        scenarios are not confidence intervals. Select an account to edit its
        budget or inspect records. Budgets do not enforce provider limits.
      </p>
    </div>
  );
}
