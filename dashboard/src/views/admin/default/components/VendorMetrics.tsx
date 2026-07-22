/// <reference types="react" />
/// <reference types="node" />

import Card from "components/card";
import React, { useEffect, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { CallBackendService } from "utils";
import BarChart from "components/charts/BarChart";
import { ApexOptions } from "apexcharts";
import { DatadogIcon, AWSIcon, HerokuIcon } from "../../../../components/icons";
import { Link } from "react-router-dom";
import {
  MdDownload,
  MdInsights,
  MdOpenInNew,
  MdRefresh,
  MdShowChart,
  MdTableChart,
  MdTrendingDown,
  MdTrendingUp,
} from "react-icons/md";
import {
  SourceHealthBadge,
  deriveSourceHealth,
  SourceHealthFields,
} from "./SourceHealth";

interface MonthlyMetric {
  month: string;
  cost: number;
}

interface VendorMetricsData extends SourceHealthFields {
  data: MonthlyMetric[];
  message?: string;
}

interface APIError {
  message: string;
  isConnectionError: boolean;
}

interface ForecastEntry {
  month: string;
  cost: number;
  best_case: number;
  worst_case: number;
}

interface ForecastData {
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

interface VendorMetricsProps {
  vendor: "datadog" | "aws" | "heroku";
  title: string;
  demo?: boolean;
  identifier?: string;
}

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const exactCurrencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const VENDOR_DEMO_MULTIPLIERS: Record<
  VendorMetricsProps["vendor"],
  number[]
> = {
  aws: [0.86, 0.9, 0.96, 1.02, 1.08, 1.14],
  datadog: [0.91, 0.95, 0.93, 0.99, 1.01, 1.05],
  heroku: [0.78, 0.83, 0.9, 0.96, 1.01, 1.08],
};

const VENDOR_GROWTH_RATES: Record<
  VendorMetricsProps["vendor"],
  ForecastData["growth_rates"]
> = {
  aws: { best_case: 8, trend_based: 13, worst_case: 22 },
  datadog: { best_case: 3, trend_based: 7, worst_case: 12 },
  heroku: { best_case: 5, trend_based: 9, worst_case: 15 },
};

const VENDOR_THEME: Record<
  VendorMetricsProps["vendor"],
  {
    accentClass: string;
    iconClass: string;
    iconWrapClass: string;
    chartColor: string;
  }
> = {
  aws: {
    accentClass: "text-amber-600 dark:text-amber-300",
    iconClass: "text-amber-600 dark:text-amber-300",
    iconWrapClass: "bg-amber-50 ring-amber-100 dark:bg-amber-500/10 dark:ring-amber-400/20",
    chartColor: "#d97706",
  },
  datadog: {
    accentClass: "text-brand-600 dark:text-teal-200",
    iconClass: "text-brand-600 dark:text-teal-200",
    iconWrapClass: "bg-brand-50 ring-brand-100 dark:bg-brand-500/10 dark:ring-brand-400/20",
    chartColor: "#0B63B6",
  },
  heroku: {
    accentClass: "text-teal-600 dark:text-teal-200",
    iconClass: "text-teal-600 dark:text-teal-200",
    iconWrapClass: "bg-teal-50 ring-teal-100 dark:bg-teal-500/10 dark:ring-teal-400/20",
    chartColor: "#14b8a6",
  },
};

const formatMoney = (value: number) => currencyFormatter.format(value);
const formatExactMoney = (value: number) => exactCurrencyFormatter.format(value);

const formatMonth = (month: string) => {
  const [maybeMonth, maybeYear] = month.split("-").map(Number);
  if (!maybeMonth || !maybeYear) return month;
  return new Date(maybeYear, maybeMonth - 1).toLocaleDateString("en-US", {
    month: "short",
    year: "numeric",
  });
};

const formatPercent = (value: number) =>
  `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;

const getVendorBaseAmount = (vendor: VendorMetricsProps["vendor"]) => {
  if (vendor === "datadog") return 2200;
  if (vendor === "heroku") return 980;
  return 15600;
};

const getVendorIcon = (vendor: VendorMetricsProps["vendor"]) => {
  if (vendor === "datadog") return DatadogIcon;
  if (vendor === "heroku") return HerokuIcon;
  return AWSIcon;
};

const getVendorLabel = (vendor: VendorMetricsProps["vendor"]) => {
  if (vendor === "aws") return "AWS";
  return vendor.charAt(0).toUpperCase() + vendor.slice(1);
};

const getRecentMonths = (count: number) => {
  const currentDate = new Date();
  return Array.from({ length: count }, (_, i) => {
    const d = new Date();
    d.setMonth(currentDate.getMonth() - (count - 1 - i));
    return d
      .toLocaleDateString("en-US", { month: "2-digit", year: "numeric" })
      .replace("/", "-");
  });
};

const getFutureMonths = (count: number) => {
  const currentDate = new Date();
  return Array.from({ length: count }, (_, i) => {
    const d = new Date();
    d.setMonth(currentDate.getMonth() + i + 1);
    return d
      .toLocaleDateString("en-US", { month: "2-digit", year: "numeric" })
      .replace("/", "-");
  });
};

const generateDemoMetrics = (
  vendor: VendorMetricsProps["vendor"],
): VendorMetricsData => {
  const months = getRecentMonths(6);
  const baseAmount = getVendorBaseAmount(vendor);
  const now = Date.now();
  const data = months.map((month, index) => ({
    month,
    cost: Math.round(baseAmount * VENDOR_DEMO_MULTIPLIERS[vendor][index]),
  }));

  // Demo two distinct health states so the freshness surfacing is visible.
  const health: SourceHealthFields =
    vendor === "aws"
      ? {
          last_success_at: new Date(now - 26 * 60 * 60 * 1000).toISOString(),
          last_attempt_at: new Date(now - 1 * 60 * 60 * 1000).toISOString(),
          last_attempt_status: "failed",
          data_through: months[months.length - 2],
          record_count: data.length,
        }
      : {
          last_success_at: new Date(now - 3 * 60 * 60 * 1000).toISOString(),
          last_attempt_at: new Date(now - 3 * 60 * 60 * 1000).toISOString(),
          last_attempt_status: "success",
          data_through: months[months.length - 1],
          record_count: data.length,
        };

  return {
    ...health,
    data,
  };
};

const generateDemoForecast = (
  vendor: VendorMetricsProps["vendor"],
): ForecastData => {
  const months = getFutureMonths(6);
  const rates = VENDOR_GROWTH_RATES[vendor];
  const baseAmount = getVendorBaseAmount(vendor) * 1.1;

  const forecast = months.map((month, index) => {
    const trendCost = baseAmount * (1 + rates.trend_based / 100) ** index;
    return {
      month,
      cost: Math.round(trendCost),
      best_case: Math.round(baseAmount * (1 + rates.best_case / 100) ** index),
      worst_case: Math.round(
        baseAmount * (1 + rates.worst_case / 100) ** index,
      ),
    };
  });

  return {
    forecast,
    sums: {
      total_best_case: forecast.reduce((sum, item) => sum + item.best_case, 0),
      total_forecast: forecast.reduce((sum, item) => sum + item.cost, 0),
      total_worst_case: forecast.reduce((sum, item) => sum + item.worst_case, 0),
    },
    growth_rates: rates,
  };
};

const getMonthlyChange = (data: MonthlyMetric[]) => {
  if (data.length < 2) return 0;
  const currentMonth = data[data.length - 1];
  const previousMonth = data[data.length - 2];
  if (!previousMonth.cost) return 0;
  return ((currentMonth.cost - previousMonth.cost) / previousMonth.cost) * 100;
};

const getAverageCost = (data: MonthlyMetric[]) =>
  data.reduce((sum, item) => sum + item.cost, 0) / Math.max(data.length, 1);

const MetricStat = ({
  label,
  value,
  caption,
  valueClassName = "text-navy-700 dark:text-white",
}: {
  label: string;
  value: string;
  caption: string;
  valueClassName?: string;
}) => (
  <div className="min-w-0 px-4 py-3">
    <dt className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">
      {label}
    </dt>
    <dd className={`mt-1 truncate text-xl font-bold ${valueClassName}`}>
      {value}
    </dd>
    <p className="mt-1 truncate text-xs text-gray-600 dark:text-gray-400">
      {caption}
    </p>
  </div>
);

const SummaryMetrics: React.FC<{
  data: MonthlyMetric[];
  metrics: VendorMetricsData;
}> = ({ data, metrics }) => {
  const currentMonth = data[data.length - 1];
  const monthlyChange = getMonthlyChange(data);
  const average = getAverageCost(data);
  const trendClass =
    monthlyChange > 0
      ? "text-red-500"
      : monthlyChange < 0
      ? "text-green-500"
      : "text-gray-700 dark:text-gray-200";

  return (
    <dl className="grid overflow-hidden rounded-md border border-gray-200 bg-gray-50/60 divide-y divide-gray-200 dark:border-white/10 dark:bg-white/5 dark:divide-white/10 sm:grid-cols-4 sm:divide-x sm:divide-y-0">
      <MetricStat
        label="Current period"
        value={formatMoney(currentMonth.cost)}
        caption={formatMonth(currentMonth.month)}
      />
      <MetricStat
        label="Month change"
        value={formatPercent(monthlyChange)}
        caption="latest vs prior month"
        valueClassName={trendClass}
      />
      <MetricStat
        label="Trailing average"
        value={formatMoney(average)}
        caption={`${data.length} observed months`}
      />
      <MetricStat
        label="Source records"
        value={`${metrics.record_count ?? data.length}`}
        caption={
          metrics.data_through
            ? `complete through ${formatMonth(metrics.data_through)}`
            : "reported by source"
        }
      />
    </dl>
  );
};

const TrendIndicator: React.FC<{ data: MonthlyMetric[] }> = ({ data }) => {
  const monthlyChange = getMonthlyChange(data);
  const isIncrease = monthlyChange >= 0;
  const Icon = isIncrease ? MdTrendingUp : MdTrendingDown;

  return (
    <div className="flex items-center gap-2 text-sm">
      <span
        className={`inline-flex items-center gap-1 font-semibold ${
          isIncrease ? "text-red-500" : "text-green-500"
        }`}
      >
        <Icon className="h-4 w-4" aria-hidden="true" />
        {formatPercent(monthlyChange)}
      </span>
      <span className="text-gray-600 dark:text-gray-400">
        latest monthly movement
      </span>
    </div>
  );
};

const VarianceCue: React.FC<{
  data: MonthlyMetric[];
  vendorLabel: string;
}> = ({ data, vendorLabel }) => {
  const currentMonth = data[data.length - 1];
  const average = getAverageCost(data.slice(0, -1));
  const variance = average
    ? ((currentMonth.cost - average) / average) * 100
    : getMonthlyChange(data);
  const needsReview = variance > 8;

  return (
    <div className="mt-5 rounded-md border border-brand-100 bg-brand-50/70 p-4 dark:border-brand-400/20 dark:bg-brand-500/10">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex gap-3">
          <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-white text-brand-600 ring-1 ring-brand-100 dark:bg-navy-900 dark:text-teal-200 dark:ring-white/10">
            <MdInsights className="h-5 w-5" aria-hidden="true" />
          </span>
          <div>
            <p className="text-sm font-bold text-navy-700 dark:text-white">
              {needsReview ? "Variance needs attention" : "Variance within range"}
            </p>
            <p className="mt-1 text-sm leading-6 text-gray-700 dark:text-gray-300">
              {vendorLabel} is {Math.abs(variance).toFixed(1)}%{" "}
              {variance >= 0 ? "above" : "below"} its trailing baseline for{" "}
              {formatMonth(currentMonth.month)}.
            </p>
          </div>
        </div>
        <span className="whitespace-nowrap rounded-md bg-white px-3 py-1 text-xs font-semibold text-brand-700 ring-1 ring-brand-100 dark:bg-navy-900 dark:text-teal-200 dark:ring-white/10">
          Current metrics
        </span>
      </div>
    </div>
  );
};

const CostBreakdownTable: React.FC<{ data: MonthlyMetric[] }> = ({ data }) => {
  const sortedData = [...data].sort((a, b) => b.cost - a.cost);
  const average = getAverageCost(data);

  return (
    <div className="mt-6 grid gap-5 lg:grid-cols-[1fr_1fr]">
      <div>
        <h3 className="text-sm font-bold text-navy-700 dark:text-white">
          Highest cost periods
        </h3>
        <div className="mt-3 space-y-3">
          {sortedData.slice(0, 3).map((item) => (
            <div
              key={item.month}
              className="flex items-center justify-between border-b border-gray-200 pb-2 text-sm last:border-b-0 dark:border-white/10"
            >
              <span className="text-gray-600 dark:text-gray-400">
                {formatMonth(item.month)}
              </span>
              <span className="font-semibold text-navy-700 dark:text-white">
                {formatMoney(item.cost)}
              </span>
            </div>
          ))}
        </div>
      </div>
      <div>
        <h3 className="text-sm font-bold text-navy-700 dark:text-white">
          Evidence summary
        </h3>
        <div className="mt-3 space-y-3 text-sm">
          <div className="flex items-center justify-between border-b border-gray-200 pb-2 dark:border-white/10">
            <span className="text-gray-600 dark:text-gray-400">Average</span>
            <span className="font-semibold text-navy-700 dark:text-white">
              {formatMoney(average)}
            </span>
          </div>
          <div className="flex items-center justify-between border-b border-gray-200 pb-2 dark:border-white/10">
            <span className="text-gray-600 dark:text-gray-400">Lowest</span>
            <span className="font-semibold text-navy-700 dark:text-white">
              {formatMoney(Math.min(...data.map((d) => d.cost)))}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-600 dark:text-gray-400">Highest</span>
            <span className="font-semibold text-navy-700 dark:text-white">
              {formatMoney(Math.max(...data.map((d) => d.cost)))}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

const ForecastSummary: React.FC<{ forecastData: ForecastData }> = ({
  forecastData,
}) => (
  <dl className="mb-6 grid overflow-hidden rounded-md border border-gray-200 bg-gray-50/60 divide-y divide-gray-200 dark:border-white/10 dark:bg-white/5 dark:divide-white/10 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
    <MetricStat
      label="Best case"
      value={formatMoney(forecastData.sums.total_best_case)}
      caption={`${forecastData.growth_rates.best_case}% monthly growth`}
      valueClassName="text-green-600 dark:text-green-300"
    />
    <MetricStat
      label="Trend forecast"
      value={formatMoney(forecastData.sums.total_forecast)}
      caption={`${forecastData.growth_rates.trend_based}% monthly growth`}
    />
    <MetricStat
      label="Worst case"
      value={formatMoney(forecastData.sums.total_worst_case)}
      caption={`${forecastData.growth_rates.worst_case}% monthly growth`}
      valueClassName="text-red-500"
    />
  </dl>
);

const VendorMetrics: React.FC<VendorMetricsProps> = ({
  vendor,
  title,
  demo = false,
  identifier,
}) => {
  const [metrics, setMetrics] = useState<VendorMetricsData | null>(null);
  const [forecastData, setForecastData] = useState<ForecastData | null>(null);
  const [error, setError] = useState<APIError | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [forecastLoading, setForecastLoading] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"actual" | "forecast">("actual");
  const { getAccessTokenSilently } = useAuth0();
  const vendorLabel = getVendorLabel(vendor);
  const VendorIcon = getVendorIcon(vendor);
  const configurationIdentifier = identifier || "Default Configuration";
  const theme = VENDOR_THEME[vendor];

  const fetchForecastData = async () => {
    try {
      setForecastLoading(true);
      if (demo) {
        setForecastData(generateDemoForecast(vendor));
        setError(null);
        return;
      }

      const response = await CallBackendService(
        `/v1/vendors-forecast/${vendor}?identifier=${encodeURIComponent(
          configurationIdentifier,
        )}`,
        getAccessTokenSilently,
      );
      setForecastData(response);
      setError(null);
    } catch (error: any) {
      console.error("Error fetching forecast data:", error);
      setError({
        message: "Failed to load forecast data",
        isConnectionError:
          error.message?.includes("Failed to fetch") || !error.response,
      });
    } finally {
      setForecastLoading(false);
    }
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      if (demo) {
        setMetrics(generateDemoMetrics(vendor));
        setError(null);
        return;
      }

      const response = await CallBackendService(
        `/v1/vendors-metrics/${vendor.toLowerCase()}?identifier=${encodeURIComponent(
          configurationIdentifier,
        )}`,
        getAccessTokenSilently,
      );
      setMetrics(response);
      setError(null);
    } catch (error: any) {
      console.error(error);
      setError({
        message: error.message || "Failed to fetch vendor metrics",
        isConnectionError:
          error.message?.includes("Failed to fetch") || !error.response,
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "forecast") {
      fetchForecastData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vendor, getAccessTokenSilently]);

  const getBarChartData = () => {
    if (!metrics?.data || !Array.isArray(metrics.data))
      return [{ name: "Monthly Cost", data: [], color: theme.chartColor }];
    return [
      {
        name: "Monthly Cost",
        data: metrics.data.map((entry: MonthlyMetric) => entry.cost),
        color: theme.chartColor,
      },
    ];
  };

  const getChartOptions = (data: MonthlyMetric[]): ApexOptions => ({
    chart: {
      toolbar: { show: false },
      foreColor: "#64748b",
      fontFamily: "DM Sans, sans-serif",
    },
    grid: {
      borderColor: "#e5e7eb",
      strokeDashArray: 4,
    },
    xaxis: {
      categories: data.map((entry: MonthlyMetric) => formatMonth(entry.month)),
      labels: {
        show: true,
        style: { colors: "#64748b", fontSize: "12px", fontWeight: 600 },
      },
      axisBorder: { show: false },
      axisTicks: { show: false },
    },
    yaxis: {
      show: true,
      labels: {
        show: true,
        style: { colors: "#64748b", fontSize: "12px", fontWeight: 600 },
        formatter: (value: number) => formatMoney(value),
      },
    },
    fill: {
      type: "gradient",
      gradient: {
        type: "vertical",
        shadeIntensity: 0.1,
        opacityFrom: 0.9,
        opacityTo: 0.55,
      },
    },
    dataLabels: { enabled: false },
    plotOptions: { bar: { borderRadius: 4, columnWidth: "42%" } },
    annotations: {
      yaxis: [
        {
          y: getAverageCost(data),
          borderColor: "#14b8a6",
          strokeDashArray: 5,
          label: {
            text: "Avg",
            borderColor: "#14b8a6",
            style: { color: "#0f172a", background: "#ccfbf1" },
          },
        },
      ],
    },
    tooltip: {
      theme: "dark",
      y: {
        formatter: (value) => formatExactMoney(value),
      },
    },
  });

  const handleExportCSV = async () => {
    try {
      const token = await getAccessTokenSilently();
      const backendUrl = process.env.REACT_APP_BACKEND_URL || "";
      const query = new URLSearchParams({
        format: "csv",
        identifier: configurationIdentifier,
      });
      const response = await fetch(
        `${backendUrl}/v1/vendors-forecast/${vendor}?${query.toString()}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${vendor}_forecast.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Export failed:", error);
    }
  };

  if (loading) {
    return (
      <Card extra="overflow-hidden !p-0 bg-white dark:!bg-gray-800">
        <div className="flex h-64 items-center justify-center">
          <div className="text-center">
            <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-solid border-brand-500 border-t-transparent"></div>
            <p className="text-gray-600 dark:text-gray-400">
              Loading source evidence...
            </p>
          </div>
        </div>
      </Card>
    );
  }

  if (error && !metrics) {
    return (
      <Card extra="overflow-hidden !p-0 bg-white dark:!bg-gray-800">
        <div className="flex h-64 items-center justify-center p-6">
          <div className="max-w-sm text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-md bg-red-50 text-red-500 dark:bg-red-500/10">
              <MdRefresh className="h-6 w-6" aria-hidden="true" />
            </div>
            <p className="mb-2 font-semibold text-red-500">
              {error.isConnectionError ? "API connection error" : error.message}
            </p>
            {error.isConnectionError ? (
              <p className="text-sm leading-6 text-gray-600 dark:text-gray-400">
                The dashboard could not reach the API server. Retry the source
                refresh when the backend is available.
              </p>
            ) : null}
            <button
              onClick={() => {
                setError(null);
                setLoading(true);
                fetchData();
              }}
              className="mt-4 inline-flex items-center gap-2 rounded-md bg-brand-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-600"
            >
              <MdRefresh className="h-4 w-4" aria-hidden="true" />
              Retry
            </button>
          </div>
        </div>
      </Card>
    );
  }

  const health = deriveSourceHealth(metrics);
  const hasMetrics = metrics?.data && metrics.data.length > 0;

  return (
    <Card extra="overflow-hidden !p-0 bg-white dark:!bg-gray-800">
      <header className="border-b border-gray-200 p-5 dark:border-white/10">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex min-w-0 items-start gap-4">
            <div
              className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-md ring-1 ${theme.iconWrapClass}`}
            >
              <VendorIcon className={`h-6 w-6 ${theme.iconClass}`} />
            </div>
            <div className="min-w-0">
              <p
                className={`text-xs font-semibold uppercase ${theme.accentClass}`}
              >
                {vendorLabel} source
              </p>
              <h5 className="mt-1 truncate text-lg font-bold text-navy-700 dark:text-white">
                {title}
              </h5>
              <p className="mt-1 truncate text-sm text-gray-600 dark:text-gray-400">
                {configurationIdentifier}
              </p>
            </div>
          </div>
          <SourceHealthBadge health={health} />
        </div>
      </header>

      <section className="p-5">
        <div className="mb-5 flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h2 className="text-xl font-bold text-navy-700 dark:text-white">
              Cost evidence
            </h2>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Observed spend, freshness, and forecast envelope for this source.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-md border border-gray-200 bg-gray-50 p-1 dark:border-white/10 dark:bg-white/5">
              <button
                onClick={() => setActiveTab("actual")}
                className={`inline-flex items-center gap-2 rounded px-3 py-2 text-sm font-semibold transition-colors ${
                  activeTab === "actual"
                    ? "bg-white text-brand-700 shadow-sm dark:bg-navy-900 dark:text-white"
                    : "text-gray-600 hover:text-navy-700 dark:text-gray-300 dark:hover:text-white"
                }`}
              >
                <MdTableChart className="h-4 w-4" aria-hidden="true" />
                Actual
              </button>
              <button
                onClick={() => setActiveTab("forecast")}
                className={`inline-flex items-center gap-2 rounded px-3 py-2 text-sm font-semibold transition-colors ${
                  activeTab === "forecast"
                    ? "bg-white text-brand-700 shadow-sm dark:bg-navy-900 dark:text-white"
                    : "text-gray-600 hover:text-navy-700 dark:text-gray-300 dark:hover:text-white"
                }`}
              >
                <MdShowChart className="h-4 w-4" aria-hidden="true" />
                Forecast
              </button>
            </div>

            {activeTab === "forecast" && !demo ? (
              <button
                onClick={handleExportCSV}
                className="inline-flex items-center gap-2 rounded-md border border-gray-200 px-3 py-2 text-sm font-semibold text-navy-700 transition-colors hover:border-brand-200 hover:bg-brand-50 dark:border-white/10 dark:text-white dark:hover:bg-white/10"
              >
                <MdDownload className="h-4 w-4" aria-hidden="true" />
                Export
              </button>
            ) : null}

            <Link
              to={demo ? "/auth/sign-in" : `/admin/vendors/${vendor}`}
              className="inline-flex items-center gap-2 rounded-md bg-brand-500 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-600"
            >
              {demo ? "Connect source" : "Details"}
              <MdOpenInNew className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        </div>

        {activeTab === "actual" ? (
          hasMetrics ? (
            <>
              <SummaryMetrics data={metrics.data} metrics={metrics} />
              <div className="mt-5 h-[280px] w-full">
                <BarChart
                  chartData={getBarChartData()}
                  chartOptions={getChartOptions(metrics.data)}
                />
              </div>
              <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <TrendIndicator data={metrics.data} />
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {metrics.data_through
                    ? `Data through ${formatMonth(metrics.data_through)}`
                    : "Data range reported by the source API"}
                </p>
              </div>
              <VarianceCue data={metrics.data} vendorLabel={vendorLabel} />
              <CostBreakdownTable data={metrics.data} />
              <div className="mt-6 overflow-x-auto">
                <table className="w-full min-w-[420px] text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 text-xs uppercase text-gray-500 dark:border-white/10 dark:text-gray-400">
                      <th className="py-3 text-left font-semibold">Month</th>
                      <th className="py-3 text-right font-semibold">Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.data.map((entry) => (
                      <tr
                        key={entry.month}
                        className="border-b border-gray-100 last:border-b-0 dark:border-white/5"
                      >
                        <td className="py-3 text-gray-700 dark:text-gray-300">
                          {formatMonth(entry.month)}
                        </td>
                        <td className="py-3 text-right font-semibold text-navy-700 dark:text-white">
                          {formatExactMoney(entry.cost)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="flex h-64 items-center justify-center rounded-md border border-dashed border-gray-300 dark:border-white/20">
              <p className="text-center text-gray-500">
                No API configuration found for {vendorLabel}.
              </p>
            </div>
          )
        ) : (
          <>
            {forecastLoading ? (
              <div className="flex h-64 items-center justify-center">
                <div className="text-center">
                  <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-solid border-brand-500 border-t-transparent"></div>
                  <p className="text-gray-600 dark:text-gray-400">
                    Loading forecast data...
                  </p>
                </div>
              </div>
            ) : error ? (
              <div className="flex h-64 items-center justify-center rounded-md border border-dashed border-red-200 bg-red-50/50 p-6 text-center dark:border-red-400/20 dark:bg-red-500/10">
                <p className="text-sm font-semibold text-red-500">
                  {error.message}
                </p>
              </div>
            ) : forecastData?.forecast &&
              Array.isArray(forecastData.forecast) &&
              forecastData.forecast.length > 0 ? (
              <>
                <ForecastSummary forecastData={forecastData} />
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[620px] text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 text-xs uppercase text-gray-500 dark:border-white/10 dark:text-gray-400">
                        <th className="py-3 text-left font-semibold">Month</th>
                        <th className="py-3 text-right font-semibold">
                          Best case
                        </th>
                        <th className="py-3 text-right font-semibold">
                          Trend forecast
                        </th>
                        <th className="py-3 text-right font-semibold">
                          Worst case
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {forecastData.forecast.map((entry) => (
                        <tr
                          key={entry.month}
                          className="border-b border-gray-100 last:border-b-0 dark:border-white/5"
                        >
                          <td className="py-3 text-gray-700 dark:text-gray-300">
                            {formatMonth(entry.month)}
                          </td>
                          <td className="py-3 text-right font-semibold text-green-600 dark:text-green-300">
                            {formatExactMoney(entry.best_case)}
                          </td>
                          <td className="py-3 text-right font-semibold text-navy-700 dark:text-white">
                            {formatExactMoney(entry.cost)}
                          </td>
                          <td className="py-3 text-right font-semibold text-red-500">
                            {formatExactMoney(entry.worst_case)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <div className="flex h-64 items-center justify-center rounded-md border border-dashed border-gray-300 dark:border-white/20">
                <p className="text-gray-500">No forecast data available.</p>
              </div>
            )}
          </>
        )}
      </section>
    </Card>
  );
};

export default VendorMetrics;
