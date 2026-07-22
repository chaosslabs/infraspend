import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import {
  MdHelpOutline,
  MdLogin,
  MdManageAccounts,
  MdPreview,
  MdShowChart,
  MdTableChart,
} from "react-icons/md";
import { SiDatadog, SiAmazonaws, SiHeroku } from "react-icons/si";
import InfraSpendLogo from "components/logo/InfraSpendLogo";
import { trackPageView, trackEvent } from "../../utils/gtm";

const FEATURE_CARDS = [
  {
    icon: <MdManageAccounts className="h-6 w-6" aria-hidden="true" />,
    title: "Linked accounts",
    description: "Configure AWS, Datadog, and Heroku cost sources.",
  },
  {
    icon: <MdTableChart className="h-6 w-6" aria-hidden="true" />,
    title: "Monthly metrics",
    description: "Track vendor spend with source freshness visible.",
  },
  {
    icon: <MdShowChart className="h-6 w-6" aria-hidden="true" />,
    title: "Forecast budgets",
    description: "Export forecasts and maintain vendor budget plans.",
  },
];

export default function SignIn() {
  const { loginWithRedirect } = useAuth0();

  useEffect(() => {
    trackPageView("/", "Sign In");
  }, []);

  const handleSignIn = () => {
    trackEvent("auth", "sign_in_click");
    loginWithRedirect();
  };

  const handleDemoClick = () => {
    trackEvent("demo", "demo_dashboard_click");
  };

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-[1180px] flex-col justify-center gap-8 px-5 py-12">
      <section className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
        <div>
          <InfraSpendLogo className="mb-8 w-full max-w-[360px] text-white" />
          <p className="text-sm font-semibold uppercase text-teal-200">
            Open source FinOps dashboard
          </p>
          <h1 className="mt-3 max-w-3xl text-4xl font-bold leading-tight text-white md:text-5xl">
            Cost visibility for linked cloud and SaaS accounts.
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-gray-300">
            InfraSpend brings account configuration, monthly metrics, source
            freshness, forecasts, CSV export, and budget planning into one
            focused workspace.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <button
              onClick={handleSignIn}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-brand-500 px-5 py-3 text-base font-semibold text-white transition-colors hover:bg-brand-600"
            >
              <MdLogin className="h-5 w-5" aria-hidden="true" />
              Sign in
            </button>
            <Link
              to="/demo"
              onClick={handleDemoClick}
              className="inline-flex items-center justify-center gap-2 rounded-md border border-white/15 px-5 py-3 text-base font-semibold text-white transition-colors hover:bg-white/10"
            >
              <MdPreview className="h-5 w-5" aria-hidden="true" />
              View demo
            </Link>
            <Link
              to="/auth/support"
              className="inline-flex items-center justify-center gap-2 rounded-md px-5 py-3 text-base font-semibold text-gray-300 transition-colors hover:bg-white/10 hover:text-white"
            >
              <MdHelpOutline className="h-5 w-5" aria-hidden="true" />
              Support
            </Link>
          </div>
        </div>

        <div className="rounded-lg border border-white/10 bg-white/[0.04] p-5 shadow-2xl shadow-black/10 backdrop-blur">
          <div className="grid gap-4">
            {FEATURE_CARDS.map((feature) => (
              <div
                key={feature.title}
                className="rounded-md border border-white/10 bg-white/[0.04] p-4"
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-md bg-teal-400/10 text-teal-200 ring-1 ring-teal-300/20">
                    {feature.icon}
                  </span>
                  <div>
                    <h2 className="font-bold text-white">{feature.title}</h2>
                    <p className="mt-1 text-sm leading-6 text-gray-300">
                      {feature.description}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 border-t border-white/10 pt-5">
            <p className="text-xs font-semibold uppercase text-gray-400">
              Supported sources
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <IntegrationBadge
                icon={<SiAmazonaws className="h-5 w-5" aria-hidden="true" />}
                label="AWS"
              />
              <IntegrationBadge
                icon={<SiDatadog className="h-5 w-5" aria-hidden="true" />}
                label="Datadog"
              />
              <IntegrationBadge
                icon={<SiHeroku className="h-5 w-5" aria-hidden="true" />}
                label="Heroku"
              />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

const IntegrationBadge = ({
  icon,
  label,
}: {
  icon: React.ReactNode;
  label: string;
}) => (
  <div className="flex items-center gap-2 rounded-md border border-white/10 bg-white/[0.04] px-3 py-2 text-white">
    <span className="text-teal-200">{icon}</span>
    <span className="text-sm font-semibold">{label}</span>
  </div>
);
