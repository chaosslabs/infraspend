import React from "react";
import { Link } from "react-router-dom";
import VendorMetrics from "views/admin/default/components/VendorMetrics";
import InfraSpendLogo from "components/logo/InfraSpendLogo";

export default function DemoDashboard() {
  return (
    <div className="min-h-screen bg-lightPrimary dark:!bg-navy-900">
      <main className="mx-auto flex h-full min-h-screen flex-col gap-8 p-6">
        <div className="mx-auto w-full max-w-[1200px]">
          {/* Header */}
          <div className="mb-8 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <InfraSpendLogo className="h-12 w-auto text-navy-700 dark:text-white" />
              <h1 className="text-2xl font-bold text-navy-700 dark:text-white">
                InfraSpend Demo
              </h1>
            </div>
            <Link
              to="/auth/sign-in"
              className="rounded-xl bg-brand-500 px-4 py-2 text-base font-medium text-white transition duration-200 hover:bg-brand-600"
            >
              ← Back to Sign In
            </Link>
          </div>

          {/* Demo Notice */}
          <div className="mb-8 rounded-xl bg-indigo-50 p-4 dark:bg-navy-800">
            <p className="text-center text-gray-700 dark:text-gray-300">
              This is a demo dashboard showing sample data. 
              <Link to="/auth/sign-in" className="ml-2 font-medium text-brand-500 hover:text-brand-600">
                Sign in to access the full dashboard →
              </Link>
            </p>
          </div>

          {/* Metrics */}
          <div className="grid gap-6 md:grid-cols-2">
            <VendorMetrics vendor="datadog" identifier="Default Configuration" title="Datadog Metrics" demo={true} />
            <VendorMetrics vendor="aws" identifier="Default Configuration" title="AWS Metrics" demo={true} />
            <VendorMetrics vendor="heroku" identifier="Default Configuration" title="Heroku Metrics" demo={true} />
          </div>
        </div>
      </main>
    </div>
  );
} 
