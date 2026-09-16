import { PlanningWorkspace } from "views/admin/planning";
import React from "react";
import { Link } from "react-router-dom";
import { MdArrowBack, MdLogin } from "react-icons/md";

import VendorMetrics from "views/admin/default/components/VendorMetrics";
import InfraSpendLogo from "components/logo/InfraSpendLogo";

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
                Plan your AI spend
              </h1>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              to="/admin/default"
              className="inline-flex items-center gap-2 rounded-md border border-gray-200 px-4 py-2 text-sm font-semibold text-navy-700 transition-colors hover:border-brand-200 hover:bg-white dark:border-white/10 dark:text-white dark:hover:bg-white/10"
            >
              <MdArrowBack className="h-4 w-4" aria-hidden="true" />
              Back to workspace
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

        <section>
          <h2 className="is-title">Can this workload stay within budget?</h2>
          <p className="is-muted mb-6 mt-2">
            Try a plan, adjust one assumption, and track an action. No
            credentials needed.
          </p>
          <PlanningWorkspace demo />
        </section>
        <details>
          <summary className="cursor-pointer font-semibold">
            Explore sample source records
          </summary>
          <div className="mb-4 mt-5 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="text-xl font-bold text-navy-700 dark:text-white">
                7 sample sources
              </h2>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                Sample source data shows the actual metrics and forecast UI
                without requiring credentials.
              </p>
            </div>
            <span className="text-sm font-semibold text-brand-600 dark:text-teal-200">
              Cloud / AI APIs / Subscriptions
            </span>
          </div>
          <div className="grid gap-5 2xl:grid-cols-2">
            <VendorMetrics
              vendor="anthropic"
              demo
              title="Claude API cost evidence"
            />
            <VendorMetrics
              vendor="openai"
              demo
              title="OpenAI API cost evidence"
            />
            <VendorMetrics
              vendor="claude"
              demo
              title="Claude subscription costs"
            />
            <VendorMetrics
              vendor="chatgpt"
              demo
              title="ChatGPT subscription costs"
            />
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
        </details>
      </main>
    </div>
  );
};

export default DemoDashboard;
