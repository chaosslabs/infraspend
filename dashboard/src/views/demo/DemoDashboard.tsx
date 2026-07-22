import React from "react";
import { Link } from "react-router-dom";
import {
  MdArrowBack,
  MdDownload,
  MdLogin,
  MdManageAccounts,
  MdShowChart,
  MdTableChart,
} from "react-icons/md";
import Card from "components/card";
import VendorMetrics from "views/admin/default/components/VendorMetrics";
import InfraSpendLogo from "components/logo/InfraSpendLogo";

const DEMO_SIGNALS = [
  {
    label: "Linked sources",
    value: "3",
    detail: "AWS, Datadog, Heroku",
  },
  {
    label: "Sample window",
    value: "6 mo",
    detail: "monthly cost records",
  },
  {
    label: "Forecast horizon",
    value: "6 mo",
    detail: "best, trend, worst cases",
  },
];

const FEATURE_CARDS = [
  {
    title: "Linked accounts",
    detail: "The authenticated app configures AWS, Datadog, and Heroku sources.",
    icon: <MdManageAccounts className="h-5 w-5" aria-hidden="true" />,
  },
  {
    title: "Monthly metrics",
    detail: "Vendor cards show historical spend, source freshness, and variance.",
    icon: <MdTableChart className="h-5 w-5" aria-hidden="true" />,
  },
  {
    title: "Forecasts and budgets",
    detail: "Forecast tables can be exported, and vendor details support budgets.",
    icon: <MdShowChart className="h-5 w-5" aria-hidden="true" />,
  },
  {
    title: "CSV export",
    detail: "CSV export is available from the authenticated forecast view.",
    icon: <MdDownload className="h-5 w-5" aria-hidden="true" />,
  },
];

const DemoDashboard = () => {
  return (
    <div className="min-h-screen bg-gray-50 text-navy-700 dark:!bg-navy-900 dark:text-white">
      <main className="mx-auto flex h-full min-h-screen w-full max-w-[1500px] flex-col gap-6 px-5 py-6 lg:px-8">
        <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <InfraSpendLogo className="h-10 w-auto text-navy-700 dark:text-white" />
            <div>
              <p className="text-sm font-semibold uppercase text-brand-600 dark:text-teal-200">
                Demo workspace
              </p>
              <h1 className="text-2xl font-bold text-navy-700 dark:text-white">
                InfraSpend dashboard preview
              </h1>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              to="/auth/sign-in"
              className="inline-flex items-center gap-2 rounded-md border border-gray-200 px-4 py-2 text-sm font-semibold text-navy-700 transition-colors hover:border-brand-200 hover:bg-white dark:border-white/10 dark:text-white dark:hover:bg-white/10"
            >
              <MdArrowBack className="h-4 w-4" aria-hidden="true" />
              Back to sign in
            </Link>
            <Link
              to="/auth/sign-in"
              className="inline-flex items-center gap-2 rounded-md bg-brand-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-600"
            >
              Sign in for live data
              <MdLogin className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        </header>

        <section className="grid gap-6 border-y border-gray-200 py-6 dark:border-white/10 xl:grid-cols-[1.1fr_0.9fr]">
          <div>
            <p className="text-sm font-semibold uppercase text-brand-600 dark:text-teal-200">
              Current product
            </p>
            <h2 className="mt-3 max-w-3xl text-3xl font-bold leading-tight text-navy-700 dark:text-white">
              A cleaner operating view for linked cloud and SaaS costs.
            </h2>
            <p className="mt-4 max-w-3xl text-base leading-7 text-gray-700 dark:text-gray-300">
              This preview uses sample data in the same vendor metrics component
              as the authenticated dashboard. The live app adds account
              configuration, protected API calls, forecast export, and vendor
              budget planning.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
            {DEMO_SIGNALS.map((signal) => (
              <div
                key={signal.label}
                className="border-b border-gray-200 py-3 last:border-b-0 dark:border-white/10"
              >
                <p className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">
                  {signal.label}
                </p>
                <p className="mt-1 text-2xl font-bold text-navy-700 dark:text-white">
                  {signal.value}
                </p>
                <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                  {signal.detail}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section>
          <div className="mb-4">
            <h2 className="text-lg font-bold text-navy-700 dark:text-white">
              Existing feature coverage
            </h2>
            <p className="mt-1 text-sm leading-6 text-gray-600 dark:text-gray-400">
              The demo only includes current product surfaces. Every navigation
              target points to an existing route.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {FEATURE_CARDS.map((feature) => (
              <Card key={feature.title} extra="!p-4">
                <div className="flex h-full flex-col">
                  <div className="flex items-center gap-2 text-brand-600 dark:text-teal-200">
                    {feature.icon}
                    <p className="font-semibold">{feature.title}</p>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-gray-600 dark:text-gray-400">
                    {feature.detail}
                  </p>
                </div>
              </Card>
            ))}
          </div>
        </section>

        <section>
          <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="text-xl font-bold text-navy-700 dark:text-white">
                Demo sources
              </h2>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                Sample source data shows the actual metrics and forecast UI
                without requiring credentials.
              </p>
            </div>
            <span className="text-sm font-semibold text-brand-600 dark:text-teal-200">
              AWS / Datadog / Heroku
            </span>
          </div>
          <div className="grid gap-5 2xl:grid-cols-2">
            <VendorMetrics
              vendor="aws"
              identifier="Production organization"
              title="AWS cost evidence"
              demo={true}
            />
            <VendorMetrics
              vendor="datadog"
              identifier="Observability account"
              title="Datadog cost evidence"
              demo={true}
            />
            <VendorMetrics
              vendor="heroku"
              identifier="Platform team"
              title="Heroku cost evidence"
              demo={true}
            />
          </div>
        </section>
      </main>
    </div>
  );
};

export default DemoDashboard;
