import { MdSmartToy } from "react-icons/md";
import Card from "components/card";
import React, { useEffect, useState, useCallback } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { CallBackendService } from "utils";
import { useSearchParams, useParams, useNavigate } from "react-router-dom";
import { DatadogIcon, AWSIcon, HerokuIcon } from "components/icons";
import { useBudgetPlans, BudgetEntry } from '../hooks/useBudgetPlans';

interface MonthlyMetric {
  month: string;
  cost: number;
}

interface ForecastEntry {
  month: string;
  cost: number;
  best_case: number;
  worst_case: number;
}

interface ForecastData {
  basis?: { status: string; message: string; base_cost: number | null; base_month: string | null };
  forecast: ForecastEntry[];
  sums: {
    total_best_case: number;
    total_forecast: number;
    total_worst_case: number;
  };
  growth_rates: {
    best_case: number;
    trend_based: number;
    worst_case: number;
  };
}

interface VendorDetailsState {
  momGrowth: number;
  budgets: BudgetEntry[];
  loading: boolean;
  error: string | null;
  success?: string | null;
}

const getVendorIcon = (vendor?: string) => {
  if (vendor === "datadog") return DatadogIcon;
  if (["openai", "anthropic", "claude", "chatgpt"].includes(vendor)) return MdSmartToy;
  if (vendor === "heroku") return HerokuIcon;
  return AWSIcon;
};

const getVendorLabel = (vendor?: string) => {
  if (vendor === "openai") return "OpenAI API";
  if (vendor === "anthropic") return "Claude API";
  if (vendor === "chatgpt") return "ChatGPT subscription";
  if (vendor === "claude") return "Claude subscription";
  if (vendor === "aws") return "AWS";
  if (!vendor) return "";
  return vendor.charAt(0).toUpperCase() + vendor.slice(1);
};

const VendorDetailsContent: React.FC = () => {
  const { vendor } = useParams<{ vendor: string }>();
  const [searchParams] = useSearchParams();
  const identifier = searchParams.get("identifier") || "Default Configuration";
  const navigate = useNavigate();
  const { getAccessTokenSilently } = useAuth0();
  const [state, setState] = useState<VendorDetailsState>({
    momGrowth: 15,
    budgets: [],
    loading: true,
    error: null
  });
  const [metrics, setMetrics] = useState<MonthlyMetric[]>([]);
  const [forecastData, setForecastData] = useState<ForecastData | null>(null);
  const [, setForecastLoading] = useState<boolean>(true);
  const VendorIcon = getVendorIcon(vendor);
  const vendorLabel = getVendorLabel(vendor);

  const {
    loading: budgetLoading,
    budgetPlan,
    error: budgetError,
    legacyPlans = [],
    createBudgetPlan,
    fetchBudgetPlan
  } = useBudgetPlans(vendor, identifier);

  const fetchMetrics = useCallback(async () => {
    try {
      const response = await CallBackendService(
        `/v1/vendors-metrics/${vendor}?identifier=${encodeURIComponent(identifier)}`,
        getAccessTokenSilently
      );
      setMetrics(response.data || []);
      setState(prev => ({
        ...prev,
        loading: false
      }));
    } catch (error: any) {
      setState(prev => ({
        ...prev,
        error: error.message,
        loading: false
      }));
    }
  }, [vendor, identifier, getAccessTokenSilently]);

  const fetchForecastData = useCallback(async () => {
    try {
      setForecastLoading(true);
      const response = await CallBackendService(
        `/v1/vendors-forecast/${vendor}?identifier=${encodeURIComponent(identifier)}`,
        getAccessTokenSilently
      );
      setForecastData(response);
      setState(prev => ({
        ...prev,
        momGrowth: response.growth_rates.trend_based
      }));
    } catch (error: any) {
      setState(prev => ({
        ...prev,
        error: error.message
      }));
    } finally {
      setForecastLoading(false);
    }
  }, [vendor, identifier, getAccessTokenSilently]);

  useEffect(() => {
    fetchMetrics();
    fetchForecastData();
    fetchBudgetPlan();
  }, [fetchMetrics, fetchForecastData, fetchBudgetPlan, vendor]);

  useEffect(() => {
    setState(prev => ({ ...prev, budgets: budgetPlan?.[0]?.budgets?.budgets || [], success: budgetPlan === null ? null : prev.success }));
  }, [budgetPlan]);

  const calculateSimulatedCost = (
    forecast: ForecastEntry,
    baseAmount: number,
    growthRate: number,
    index: number,
    forecasts: ForecastEntry[]
  ): number => {
    // For the first month (current or future), use baseAmount
    if (index === 0) {
      return baseAmount * (1 + (growthRate / 100));
    }

    // For subsequent months, use the previous month's simulated cost as the base
    const prevMonthCost: number = calculateSimulatedCost(forecasts[index - 1], baseAmount, growthRate, index - 1, forecasts);
    return prevMonthCost * (1 + (growthRate / 100));
  };

  const handleMoMChange = (value: number) => {
    setState(prev => ({
      ...prev,
      momGrowth: value,
      success: null
    }));
  };

  const handleBudgetChange = async (month: string, amount: number) => {
    // Round to 2 decimal places when setting the state
    const roundedAmount = Math.round(amount * 100) / 100;
    setState(prev => ({
      ...prev,
      budgets: prev.budgets.map(budget => 
        budget.month === month ? { ...budget, amount: roundedAmount } : budget
      ),
      success: null
    }));
  };

  const handleSetupBudgetPlan = async () => {
    try {
      if (!forecastData) return;
      
      // Update budgets with forecast values
      const updatedBudgets = forecastData.forecast.map((forecast, index) => {
        const simulatedCost = state.momGrowth === forecastData.growth_rates.trend_based
          ? forecast.cost
          : calculateSimulatedCost(
              forecast,
              forecastData.basis?.base_cost ?? 0,
              state.momGrowth,
              index,
              forecastData.forecast
            );

        return {
          month: forecast.month,
          amount: simulatedCost
        };
      });

      // Only update the budgets in state, don't trigger a full reload
      setState(prev => ({
        ...prev,
        budgets: updatedBudgets,
        success: null
      }));

    } catch (error: any) {
      setState(prev => ({
        ...prev,
        error: error.message
      }));
    }
  };

  const saveBudgets = async () => {
    setState(prev => ({ ...prev, success: null, error: null }));
    try {
      // Always use createBudgetPlan - backend will handle if it's new or existing
      await createBudgetPlan(state.budgets);
      setState(prev => ({
        ...prev,
        error: null,
        success: "Budget plan saved successfully"
      }));
    } catch (error: any) {
      setState(prev => ({
        ...prev,
        error: error.message || "Failed to save budget plan",
        success: null
      }));
    }
  };

  const addBudgetMonth = () => {
    // Get the last budget month or current month if no budgets exist
    const lastBudget = state.budgets[state.budgets.length - 1];
    let nextMonth: Date;
    
    if (lastBudget) {
      const [month, year] = lastBudget.month.split('-').map(Number);
      nextMonth = new Date(year, month - 1);
      nextMonth.setMonth(nextMonth.getMonth() + 1);
    } else {
      nextMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
      nextMonth.setMonth(nextMonth.getMonth() + 1);
    }

    const newMonth = `${String(nextMonth.getMonth() + 1).padStart(2, '0')}-${nextMonth.getFullYear()}`;
    
    // Use the last forecast amount if available, otherwise 0
    const lastForecastAmount = forecastData?.forecast[forecastData.forecast.length - 1]?.cost || 0;

    setState(prev => ({
      ...prev,
      budgets: [...prev.budgets, { month: newMonth, amount: lastForecastAmount }],
      success: null
    }));
  };

  const removeBudgetMonth = (monthToRemove: string) => {
    setState(prev => ({
      ...prev,
      budgets: prev.budgets.filter(budget => budget.month !== monthToRemove),
      success: null
    }));
  };

  if (state.loading) {
    return (
      <Card extra="pb-10 p-[20px]">
        <div className="flex h-64 items-center justify-center">
          <div className="text-center">
            <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-solid border-brand-500 border-t-transparent mx-auto"></div>
            <p className="text-gray-600 dark:text-gray-400">Loading vendor details...</p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card extra="pb-10 p-[20px]">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 dark:bg-navy-700">
            <VendorIcon className="h-8 w-8 text-brand-500 dark:text-white" />
          </div>
          <h2 className="ml-4 text-2xl font-bold text-navy-700 dark:text-white">
            {vendorLabel} Details
          </h2>
          {(vendor === "claude" || vendor === "chatgpt") && <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Manual subscription entries in USD; no automatic billing sync.</p>}
        </div>
        <button
          onClick={() => navigate(-1)}
          className="rounded bg-gray-100 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-200 dark:bg-navy-700 dark:text-gray-200"
        >
          Back
        </button>
      </div>

      {(state.error || budgetError) && <p role="alert" className="mb-4 text-red-600">{state.error || budgetError}</p>}
      {budgetError && budgetPlan === null && <button onClick={fetchBudgetPlan} disabled={budgetLoading} className="mb-4 text-brand-500">Retry loading budget</button>}
      {state.success && !budgetError && <p role="status" className="mb-4 text-green-600">{state.success}</p>}
      <p className="mb-4 text-sm text-gray-600">Account: {identifier}. Budgets on this page apply only to this account.</p>
      {legacyPlans.map(plan => (
        <details key={plan.id} className="mb-4 text-sm text-gray-600">
          <summary>Previous vendor-wide budget (preserved separately)</summary>
          <p>This plan covers {vendorLabel} across accounts. It has not been assigned to this account; create an account budget below.</p>
          <ul>{plan.budgets.budgets.map(entry => <li key={entry.month}>{entry.month}: ${entry.amount.toFixed(2)}</li>)}</ul>
        </details>
      ))}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          <h3 className="mb-4 text-lg font-bold text-navy-700 dark:text-white">
            Historical Metrics
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="py-3 text-left text-sm font-semibold text-gray-600 dark:text-gray-400">Month</th>
                  <th className="py-3 text-right text-sm font-semibold text-gray-600 dark:text-gray-400">Cost</th>
                  <th className="py-3 text-right text-sm font-semibold text-gray-600 dark:text-gray-400">MoM Growth</th>
                </tr>
              </thead>
              <tbody>
                {metrics.map((metric, index) => {
                  const prevMetric = metrics[index - 1];
                  const momGrowth = prevMetric?.cost > 0
                    ? ((metric.cost - prevMetric.cost) / prevMetric.cost) * 100 
                    : 0;
                  
                  return (
                    <tr key={metric.month} className="border-b border-gray-200">
                      <td className="py-3 text-sm text-gray-700 dark:text-gray-300">{metric.month}</td>
                      <td className="py-3 text-right text-sm text-gray-700 dark:text-gray-300">
                        ${metric.cost.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 text-right text-sm">
                        <span className={`${momGrowth > 0 ? 'text-red-500' : 'text-green-500'}`}>
                          {momGrowth.toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <div className="mb-4">
            <h3 className="mb-4 text-lg font-bold text-navy-700 dark:text-white">
              Cost Forecast
            </h3>
            <p className="mb-4 text-sm text-gray-600 dark:text-gray-300" role="status">Illustrative growth scenarios, not confidence intervals. {forecastData?.basis?.message}</p>
            <div className="flex items-center space-x-4 mb-6">
              <span className="text-sm text-gray-600 dark:text-gray-400">Simulate your growth rate:</span>
              <input
                type="range"
                min="-100"
                max="100"
                value={state.momGrowth}
                onChange={(e) => handleMoMChange(Number(e.target.value))}
                className="w-full"
              />
              <span className="text-lg font-bold text-navy-700 dark:text-white">
                {state.momGrowth}%
              </span>
            </div>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleSetupBudgetPlan}
                disabled={!forecastData?.forecast.length || budgetLoading}
                className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600 transition-colors"
              >
                Set up budget plan
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="py-3 text-left text-sm font-semibold text-gray-600 dark:text-gray-400">Month</th>
                  <th className="py-3 text-right text-sm font-semibold text-gray-600 dark:text-gray-400">Lower-growth scenario</th>
                  <th className="py-3 text-right text-sm font-semibold text-gray-600 dark:text-gray-400">Forecast</th>
                  <th className="py-3 text-right text-sm font-semibold text-gray-600 dark:text-gray-400">Higher-growth scenario</th>
                  <th className="py-3 text-right text-sm font-semibold text-gray-600 dark:text-gray-400">Your Forecast</th>
                </tr>
              </thead>
              <tbody>
                {forecastData?.forecast.map((forecast, index) => {
                  const simulatedCost = state.momGrowth === forecastData.growth_rates.trend_based
                    ? forecast.cost
                    : calculateSimulatedCost(
                        forecast,
                        forecastData.basis?.base_cost ?? 0,
                        state.momGrowth,
                        index,
                        forecastData.forecast
                      );

                  return (
                    <tr key={forecast.month} className="border-b border-gray-200">
                      <td className="py-3 text-sm text-gray-700 dark:text-gray-300">
                        {forecast.month}
                      </td>
                      <td className="py-3 text-right text-sm text-green-500">
                        ${forecast.best_case.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                      </td>
                      <td className="py-3 text-right text-sm font-medium text-navy-700 dark:text-white">
                        ${forecast.cost.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                      </td>
                      <td className="py-3 text-right text-sm text-red-500">
                        ${forecast.worst_case.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                      </td>
                      <td className="py-3 text-right text-sm font-medium text-purple-600 dark:text-purple-400">
                        ${simulatedCost.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {!!forecastData?.forecast.length && (
            <div className="mt-6 grid grid-cols-4 gap-4">
              <div className="rounded-xl bg-gray-50 p-4 dark:bg-navy-800">
                <p className="text-sm text-gray-600 dark:text-gray-400">Lower-growth scenario Total</p>
                <p className="text-lg font-bold text-green-500">
                  ${forecastData.sums.total_best_case.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  <span className="mt-1 block text-sm text-gray-400">
                    MoM Growth: {forecastData.growth_rates.best_case.toFixed(1)}%
                  </span>
                </p>
              </div>
              <div className="rounded-xl bg-gray-50 p-4 dark:bg-navy-800">
                <p className="text-sm text-gray-600 dark:text-gray-400">Forecast Total</p>
                <p className="text-lg font-bold text-navy-700 dark:text-white">
                  ${forecastData.sums.total_forecast.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  <span className="mt-1 block text-sm text-gray-400">
                    MoM Growth: {forecastData.growth_rates.trend_based.toFixed(1)}%
                  </span>
                </p>
              </div>
              <div className="rounded-xl bg-gray-50 p-4 dark:bg-navy-800">
                <p className="text-sm text-gray-600 dark:text-gray-400">Higher-growth scenario Total</p>
                <p className="text-lg font-bold text-red-500">
                  ${forecastData.sums.total_worst_case.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  <span className="mt-1 block text-sm text-gray-400">
                    MoM Growth: {forecastData.growth_rates.worst_case.toFixed(1)}%
                  </span>
                </p>
              </div>
              <div className="rounded-xl bg-gray-50 p-4 dark:bg-navy-800">
                <p className="text-sm text-gray-600 dark:text-gray-400">Your Forecast Total</p>
                <p className="text-lg font-bold text-purple-600 dark:text-purple-400">
                  ${forecastData.forecast.reduce((total, forecast, index) => {
                    const simulatedCost = state.momGrowth === forecastData.growth_rates.trend_based
                      ? forecast.cost
                      : calculateSimulatedCost(
                          forecast,
                          forecastData.basis?.base_cost ?? 0,
                          state.momGrowth,
                          index,
                          forecastData.forecast
                        );
                    return total + simulatedCost;
                  }, 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  <span className="mt-1 block text-sm text-gray-400">
                    MoM Growth: {state.momGrowth.toFixed(1)}%
                  </span>
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="lg:col-span-2">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-bold text-navy-700 dark:text-white">
              Monthly Budgets
            </h3>
            <button
              onClick={addBudgetMonth}
              className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-200 dark:bg-navy-700 dark:text-gray-200 transition-colors"
            >
              Add Month
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(state.budgets || []).map((budget) => (
              <div key={budget.month} className="flex items-center space-x-4">
                <span className="w-24 text-gray-600 dark:text-gray-400">
                  {budget.month}
                </span>
                <input
                  type="number"
                  aria-label={`Budget for ${budget.month}`}
                  value={budget.amount.toFixed(2)}
                  onChange={(e) => handleBudgetChange(budget.month, Number(e.target.value))}
                  step="0.01"
                  min="0"
                  className="flex h-12 w-full items-center justify-center rounded-xl border bg-white/0 p-3 text-sm outline-none border-gray-200 dark:!border-white/10 dark:text-white"
                />
                <button
                  onClick={() => removeBudgetMonth(budget.month)}
                  className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                  title="Remove month"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-4 flex justify-end">
        <button
          onClick={saveBudgets}
          className="rounded bg-brand-500 px-4 py-2 text-white hover:bg-brand-600"
          disabled={budgetLoading || budgetPlan === null}
        >
          {budgetLoading ? 'Saving...' : 'Save Budgets'}
        </button>
      </div>
    </Card>
  );
};

// A different account gets fresh state; late requests cannot populate its editor.
const VendorDetails: React.FC = () => {
  const { vendor } = useParams<{ vendor: string }>();
  const [params] = useSearchParams();
  return <VendorDetailsContent key={JSON.stringify([vendor, params.get("identifier")])} />;
};

export default VendorDetails;
