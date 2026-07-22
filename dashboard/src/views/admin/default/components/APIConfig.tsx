import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  MdAccountTree,
  MdAddCircleOutline,
  MdCheckCircle,
  MdClose,
  MdDashboard,
  MdEdit,
  MdErrorOutline,
  MdKey,
  MdOutlineSecurity,
} from "react-icons/md";
import DatadogConfig from "./DatadogConfig";
import AWSConfig from "./AWSConfig";
import HerokuConfig from "./HerokuConfig";
import { useAPIConfigurations } from "./hooks/useAPIConfigurations";

interface VendorConfig {
  id: string;
  name: string;
  type: string;
  description: string;
  credentials: string;
  evidence: string;
  component: React.ComponentType<any>;
  icon: JSX.Element;
}

const VENDOR_CONFIGS: VendorConfig[] = [
  {
    id: "datadog",
    name: "Datadog",
    type: "datadog",
    description: "Observability spend and usage context.",
    credentials: "API key and app key",
    evidence: "Monthly costs, freshness, and forecast context",
    component: DatadogConfig,
    icon: <MdOutlineSecurity className="h-6 w-6" aria-hidden="true" />,
  },
  {
    id: "aws",
    name: "AWS",
    type: "aws",
    description: "Cloud billing source for infrastructure costs.",
    credentials: "Access key ID and secret access key",
    evidence: "Monthly spend, cached-state visibility, and forecasts",
    component: AWSConfig,
    icon: <MdAccountTree className="h-6 w-6" aria-hidden="true" />,
  },
  {
    id: "heroku",
    name: "Heroku",
    type: "heroku",
    description: "Platform invoices for personal or team accounts.",
    credentials: "API key and optional team name",
    evidence: "Invoice-backed costs, freshness, and budget planning",
    component: HerokuConfig,
    icon: <MdKey className="h-6 w-6" aria-hidden="true" />,
  },
];

interface SelectedSource {
  vendor: VendorConfig;
  config?: {
    id: number;
    type: string;
    identifier: string;
  };
}

const APIConfig = () => {
  const { configurations, loading, error, refresh } = useAPIConfigurations();
  const [selectedSource, setSelectedSource] = useState<SelectedSource | null>(
    null
  );

  useEffect(() => {
    if (!selectedSource) return;

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSelectedSource(null);
      }
    };

    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [selectedSource]);

  const getVendorByType = (type: string) => {
    return VENDOR_CONFIGS.find((vendor) => vendor.type === type);
  };

  const getConfigurationsByType = (type: string) => {
    return configurations.filter((config) => config.type === type);
  };

  const getDefaultIdentifier = (vendor: VendorConfig) => {
    const vendorConfigurations = getConfigurationsByType(vendor.type);
    return vendorConfigurations.length === 0
      ? "Default Configuration"
      : `${vendor.name} account ${vendorConfigurations.length + 1}`;
  };

  const linkedConfigurations = configurations
    .map((config) => ({
      config,
      vendor: getVendorByType(config.type),
    }))
    .filter(
      (
        entry
      ): entry is {
        config: (typeof configurations)[number];
        vendor: VendorConfig;
      } => Boolean(entry.vendor)
    );

  const hasLinkedSources = linkedConfigurations.length > 0;

  return (
    <>
      <div className="space-y-6">
        <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="rounded-lg border border-gray-200/80 bg-white p-6 shadow-sm shadow-shadow-500 dark:border-white/10 dark:bg-navy-800 dark:shadow-none">
            <p className="text-sm font-semibold uppercase text-brand-600 dark:text-teal-200">
              Source setup
            </p>
            <h2 className="mt-3 max-w-3xl text-2xl font-bold leading-tight text-navy-700 dark:text-white">
              Connect read-only billing sources and keep their evidence visible.
            </h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-gray-700 dark:text-gray-300">
              Linked accounts feed the dashboard with cost records, source
              freshness, forecast context, and budget planning for every
              configured source instance.
            </p>
          </div>

          <div className="grid rounded-lg border border-gray-200/80 bg-white shadow-sm shadow-shadow-500 dark:border-white/10 dark:bg-navy-800 dark:shadow-none">
            <div className="border-b border-gray-200/80 p-4 dark:border-white/10">
              <p className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">
                Supported sources
              </p>
              <p className="mt-1 text-2xl font-bold text-navy-700 dark:text-white">
                {VENDOR_CONFIGS.length}
              </p>
            </div>
            <div className="grid grid-cols-2 divide-x divide-gray-200/80 dark:divide-white/10">
              <div className="p-4">
                <p className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">
                  Connected
                </p>
                <p className="mt-1 text-xl font-bold text-navy-700 dark:text-white">
                  {linkedConfigurations.length}
                </p>
              </div>
              <div className="p-4">
                <p className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">
                  Status
                </p>
                <p className="mt-1 text-xl font-bold text-navy-700 dark:text-white">
                  {hasLinkedSources ? "Ready" : "Setup"}
                </p>
              </div>
            </div>
          </div>
        </section>

        {loading ? (
          <div className="rounded-lg border border-gray-200/80 bg-white p-6 text-sm text-gray-600 shadow-sm shadow-shadow-500 dark:border-white/10 dark:bg-navy-800 dark:text-gray-300 dark:shadow-none">
            Loading linked sources...
          </div>
        ) : error ? (
          <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-5 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-900/20 dark:text-red-100">
            <MdErrorOutline className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
            <p>{error}</p>
          </div>
        ) : (
          <>
            <section
              id="source-picker"
              className="grid gap-4 md:grid-cols-3"
              aria-label="Available cost sources"
            >
              {VENDOR_CONFIGS.map((vendor) => {
                const vendorConfigurations = getConfigurationsByType(
                  vendor.type
                );
                const isConnected = vendorConfigurations.length > 0;
                const accountCount = vendorConfigurations.length;
                const accountLabel =
                  accountCount === 1
                    ? "1 linked account"
                    : `${accountCount} linked accounts`;

                return (
                  <button
                    key={vendor.id}
                    type="button"
                    onClick={() => setSelectedSource({ vendor })}
                    className="group flex min-h-[260px] flex-col rounded-lg border border-gray-200/80 bg-white p-5 text-left shadow-sm shadow-shadow-500 transition-colors hover:border-brand-200 hover:bg-brand-50/40 dark:border-white/10 dark:bg-navy-800 dark:shadow-none dark:hover:border-teal-300/40 dark:hover:bg-white/5"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex h-11 w-11 items-center justify-center rounded-md bg-brand-50 text-brand-600 ring-1 ring-brand-100 dark:bg-brand-500/10 dark:text-teal-200 dark:ring-brand-400/20">
                        {vendor.icon}
                      </div>
                      <span
                        className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold ${
                          isConnected
                            ? "bg-green-50 text-green-700 dark:bg-green-500/10 dark:text-green-200"
                            : "bg-gray-100 text-gray-700 dark:bg-white/10 dark:text-gray-300"
                        }`}
                      >
                        {isConnected && (
                          <MdCheckCircle className="h-4 w-4" aria-hidden="true" />
                        )}
                        {isConnected ? accountLabel : "Not connected"}
                      </span>
                    </div>

                    <div className="mt-5 flex-1">
                      <h3 className="text-lg font-bold text-navy-700 dark:text-white">
                        {vendor.name}
                      </h3>
                      <p className="mt-2 text-sm leading-6 text-gray-600 dark:text-gray-400">
                        {vendor.description}
                      </p>
                      <div className="mt-4 space-y-3 border-t border-gray-200/80 pt-4 dark:border-white/10">
                        <div>
                          <p className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">
                            Credentials
                          </p>
                          <p className="mt-1 text-sm text-navy-700 dark:text-white">
                            {vendor.credentials}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">
                            Evidence
                          </p>
                          <p className="mt-1 text-sm leading-5 text-navy-700 dark:text-white">
                            {vendor.evidence}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="mt-5 flex items-center justify-between gap-3 border-t border-gray-200/80 pt-4 dark:border-white/10">
                      <p className="min-w-0 truncate text-sm font-medium text-gray-600 dark:text-gray-300">
                        {isConnected ? accountLabel : "Not connected"}
                      </p>
                      <span className="inline-flex shrink-0 items-center gap-2 text-sm font-semibold text-brand-600 group-hover:text-brand-700 dark:text-teal-200">
                        <MdAddCircleOutline
                          className="h-4 w-4"
                          aria-hidden="true"
                        />
                        {isConnected ? "Add another" : "Connect"}
                      </span>
                    </div>
                  </button>
                );
              })}
            </section>

            {hasLinkedSources ? (
              <section className="rounded-lg border border-gray-200/80 bg-white p-5 shadow-sm shadow-shadow-500 dark:border-white/10 dark:bg-navy-800 dark:shadow-none">
                <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
                  <div>
                    <h2 className="text-lg font-bold text-navy-700 dark:text-white">
                      Connected sources
                    </h2>
                    <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                      Account identity stays paired with the source that feeds
                      dashboard metrics and forecasts.
                    </p>
                  </div>
                  <Link
                    to="/admin/default"
                    className="inline-flex w-fit items-center gap-2 rounded-md border border-gray-200 px-3 py-2 text-sm font-semibold text-navy-700 transition-colors hover:border-brand-200 hover:bg-brand-50 dark:border-white/10 dark:text-white dark:hover:bg-white/10"
                  >
                    <MdDashboard className="h-4 w-4" aria-hidden="true" />
                    View dashboard
                  </Link>
                </div>

                <div className="divide-y divide-gray-200/80 dark:divide-white/10">
                  {linkedConfigurations.map(({ config, vendor }) => (
                    <div
                      key={`${config.type}-${config.id}`}
                      className="grid gap-4 py-4 md:grid-cols-[minmax(180px,0.5fr)_minmax(0,1fr)_auto] md:items-center"
                    >
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-brand-50 text-brand-600 ring-1 ring-brand-100 dark:bg-brand-500/10 dark:text-teal-200 dark:ring-brand-400/20">
                          {vendor.icon}
                        </div>
                        <div>
                          <p className="font-semibold text-navy-700 dark:text-white">
                            {vendor.name}
                          </p>
                          <p className="text-xs uppercase text-green-700 dark:text-green-200">
                            Connected
                          </p>
                        </div>
                      </div>

                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-navy-700 dark:text-white">
                          {config.identifier}
                        </p>
                        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                          {vendor.evidence}
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={() => setSelectedSource({ vendor, config })}
                        className="inline-flex w-fit items-center gap-2 rounded-md bg-brand-500 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-600"
                      >
                        <MdEdit className="h-4 w-4" aria-hidden="true" />
                        Edit
                      </button>
                    </div>
                  ))}
                </div>
              </section>
            ) : (
              <section className="rounded-lg border border-dashed border-brand-200 bg-brand-50/50 p-5 dark:border-teal-300/30 dark:bg-white/5">
                <p className="text-sm font-semibold text-brand-700 dark:text-teal-200">
                  Start with one read-only source.
                </p>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-700 dark:text-gray-300">
                  Once a source is connected, the dashboard can show cost
                  evidence with freshness and forecast context instead of an
                  empty setup state.
                </p>
              </section>
            )}
          </>
        )}
      </div>

      {selectedSource && (
        <div
          className="fixed inset-0 z-50 flex justify-end"
          role="dialog"
          aria-modal="true"
          aria-labelledby="source-drawer-title"
        >
          <button
            type="button"
            className="absolute inset-0 bg-navy-900/70"
            onClick={() => setSelectedSource(null)}
            aria-label="Close source setup"
          />
          <aside className="relative flex h-full w-full max-w-xl flex-col overflow-y-auto bg-white p-6 shadow-2xl dark:bg-navy-800">
            <div className="mb-6 flex items-start justify-between gap-4 border-b border-gray-200 pb-5 dark:border-white/10">
              <div>
                <p className="text-sm font-semibold uppercase text-brand-600 dark:text-teal-200">
                  Source credentials
                </p>
                <h2
                  id="source-drawer-title"
                  className="mt-2 text-2xl font-bold text-navy-700 dark:text-white"
                >
                  {selectedSource.config
                    ? `Edit ${selectedSource.vendor.name} account`
                    : getConfigurationsByType(selectedSource.vendor.type).length > 0
                    ? `Add another ${selectedSource.vendor.name} account`
                    : `Connect ${selectedSource.vendor.name}`}
                </h2>
                <p className="mt-2 text-sm leading-6 text-gray-600 dark:text-gray-400">
                  {selectedSource.config?.identifier ||
                    selectedSource.vendor.description}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedSource(null)}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-gray-200 text-gray-600 transition-colors hover:border-brand-200 hover:bg-brand-50 dark:border-white/10 dark:text-gray-300 dark:hover:bg-white/10"
                aria-label="Close source setup"
              >
                <MdClose className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>

            {React.createElement(selectedSource.vendor.component, {
              onConfigured: () => {
                refresh();
                setSelectedSource(null);
              },
              existingConfig: Boolean(selectedSource.config),
              initialIdentifier:
                selectedSource.config?.identifier ||
                getDefaultIdentifier(selectedSource.vendor),
              lockIdentifier: Boolean(selectedSource.config),
            })}
          </aside>
        </div>
      )}
    </>
  );
};

export default APIConfig;
