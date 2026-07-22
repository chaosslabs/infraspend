import { useEffect } from "react";
import { Link } from "react-router-dom";
import {
  MdAddCircleOutline,
  MdAccountTree,
  MdBarChart,
  MdCalendarMonth,
  MdRule,
} from "react-icons/md";
import Card from "components/card";
import VendorMetrics from "./components/VendorMetrics";
import { useAPIConfigurations } from "./components/hooks/useAPIConfigurations";
import { LoadingState } from "components/loading/LoadingState";

const VENDOR_TITLES: Record<string, string> = {
  datadog: "Datadog cost evidence",
  aws: "AWS cost evidence",
  heroku: "Heroku cost evidence",
};

const PRODUCT_SIGNALS = [
  {
    label: "Linked accounts",
    value: "Configured",
    detail: "AWS, Datadog, and Heroku sources",
    icon: <MdAccountTree className="h-5 w-5" aria-hidden="true" />,
  },
  {
    label: "Cost metrics",
    value: "Current",
    detail: "monthly spend and source freshness",
    icon: <MdBarChart className="h-5 w-5" aria-hidden="true" />,
  },
  {
    label: "Budget planning",
    value: "Available",
    detail: "vendor details include forecast budgets",
    icon: <MdCalendarMonth className="h-5 w-5" aria-hidden="true" />,
  },
];

const Dashboard = () => {
  const { configurations, loading } = useAPIConfigurations();
  const visibleConfigurations = configurations.filter(
    (config) => VENDOR_TITLES[config.type],
  );

  useEffect(() => {
    document.title = "Dashboard";
  }, []);

  if (loading) {
    return <LoadingState />;
  }

  if (visibleConfigurations.length === 0) {
    return (
      <div className="mx-auto mt-3 max-w-[1080px]">
        <Card extra="overflow-hidden !p-0">
          <div className="grid gap-8 p-6 md:p-8 lg:grid-cols-[minmax(0,1fr)_minmax(280px,340px)] lg:items-start">
            <section className="max-w-[720px]">
              <p className="text-sm font-semibold uppercase text-brand-600 dark:text-teal-200">
                InfraSpend setup
              </p>
              <h1 className="mt-3 max-w-2xl text-3xl font-bold leading-tight text-navy-700 dark:text-white">
                Connect your first source to build a trustworthy cost evidence
                view.
              </h1>
              <p className="mt-4 max-w-2xl text-base leading-7 text-gray-700 dark:text-gray-300">
                Start with a read-only billing source. The dashboard will keep
                freshness, records, and forecast context visible instead of
                treating every number as equally reliable.
              </p>
              <Link
                to="/admin/linked-accounts"
                className="mt-6 inline-flex items-center gap-2 rounded-md bg-brand-500 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-brand-600"
              >
                <MdAddCircleOutline className="h-5 w-5" aria-hidden="true" />
                Link an account
              </Link>
            </section>
            <aside className="max-w-xl border-t border-gray-200/80 pt-6 dark:border-white/10 lg:max-w-none lg:border-l-2 lg:border-t-0 lg:border-brand-200/60 lg:py-1 lg:pl-6 dark:lg:border-teal-300/40">
              <h2 className="text-sm font-bold uppercase text-gray-500 dark:text-gray-400">
                Setup checklist
              </h2>
              <div className="mt-4 space-y-3">
                {[
                  "Read-only provider credentials",
                  "Current source freshness",
                  "Budget plan from forecast data",
                ].map((item, index) => (
                  <div key={item} className="flex items-start gap-3">
                    <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-brand-50 text-sm font-bold text-brand-700 ring-1 ring-brand-100 dark:bg-navy-900 dark:text-teal-200 dark:ring-white/10">
                      {index + 1}
                    </span>
                    <p className="text-sm font-medium leading-6 text-navy-700 dark:text-white">
                      {item}
                    </p>
                  </div>
                ))}
              </div>
            </aside>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto mt-3 max-w-[1500px] space-y-6">
      <section className="grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
        <Card extra="overflow-hidden !p-0">
          <div className="p-6">
            <p className="text-sm font-semibold uppercase text-brand-600 dark:text-teal-200">
              Evidence-grade FinOps
            </p>
            <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <h1 className="max-w-3xl text-3xl font-bold leading-tight text-navy-700 dark:text-white">
                  Cost evidence cockpit
                </h1>
                <p className="mt-3 max-w-3xl text-base leading-7 text-gray-700 dark:text-gray-300">
                  Review spend with source freshness, historical metrics, and
                  forecast context before changing budgets.
                </p>
              </div>
              <Link
                to="/admin/linked-accounts"
                className="inline-flex w-fit items-center gap-2 rounded-md border border-gray-200 px-4 py-3 text-sm font-semibold text-navy-700 transition-colors hover:border-brand-200 hover:bg-brand-50 dark:border-white/10 dark:text-white dark:hover:bg-white/10"
              >
                <MdRule className="h-5 w-5" aria-hidden="true" />
                Manage sources
              </Link>
            </div>
          </div>
        </Card>

        <Card extra="!p-0">
          <div className="grid h-full grid-cols-3 divide-x divide-gray-200 dark:divide-white/10">
            <div className="p-5">
              <p className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">
                Sources
              </p>
              <p className="mt-2 text-2xl font-bold text-navy-700 dark:text-white">
                {visibleConfigurations.length}
              </p>
              <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                connected
              </p>
            </div>
            <div className="p-5">
              <p className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">
                Mode
              </p>
              <p className="mt-2 text-2xl font-bold text-navy-700 dark:text-white">
                Review
              </p>
              <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                source visible
              </p>
            </div>
            <div className="p-5">
              <p className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">
                Scope
              </p>
              <p className="mt-2 text-2xl font-bold text-navy-700 dark:text-white">
                Cost
              </p>
              <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                evidence first
              </p>
            </div>
          </div>
        </Card>
      </section>

      <section className="grid gap-5 md:grid-cols-3">
        {PRODUCT_SIGNALS.map((signal) => (
          <Card key={signal.label} extra="!p-5">
            <div className="flex items-start gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-brand-50 text-brand-600 ring-1 ring-brand-100 dark:bg-brand-500/10 dark:text-teal-200 dark:ring-brand-400/20">
                {signal.icon}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-gray-600 dark:text-gray-400">
                  {signal.label}
                </p>
                <p className="mt-1 text-lg font-bold text-navy-700 dark:text-white">
                  {signal.value}
                </p>
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                  {signal.detail}
                </p>
              </div>
            </div>
          </Card>
        ))}
      </section>

      <section>
        <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-xl font-bold text-navy-700 dark:text-white">
              Source review
            </h2>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Each source keeps cost, freshness, and forecast context together.
            </p>
          </div>
          <p className="text-sm font-semibold text-brand-600 dark:text-teal-200">
            {visibleConfigurations.map((config) => config.type.toUpperCase()).join(" / ")}
          </p>
        </div>
        <div className="grid grid-cols-1 gap-5 2xl:grid-cols-2">
          {visibleConfigurations.map((config) => (
            <VendorMetrics
              key={`${config.type}-${config.id}`}
              identifier={config.identifier}
              vendor={config.type as "datadog" | "aws" | "heroku"}
              title={VENDOR_TITLES[config.type]}
            />
          ))}
        </div>
      </section>
    </div>
  );
};

export default Dashboard;
