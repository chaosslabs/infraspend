import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  MdAccountTree,
  MdKey,
  MdOutlineSecurity,
  MdClose,
} from "react-icons/md";
import {
  OpenAIConfig,
  AnthropicConfig,
  ClaudeConfig,
  ChatGPTConfig,
  BillingConfigProps,
} from "./AIBillingConfig";
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
  component: React.ComponentType<BillingConfigProps>;
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
  {
    id: "openai",
    type: "openai",
    name: "OpenAI API",
    description: "Organization API spending for GPT and other OpenAI services.",
    credentials: "Organization admin API key",
    evidence: "Provider-reported API costs and forecasts",
    component: OpenAIConfig,
    icon: <MdKey className="h-6 w-6" aria-hidden="true" />,
  },
  {
    id: "anthropic",
    type: "anthropic",
    name: "Claude API (Anthropic)",
    description: "Organization API spending from Claude Console.",
    credentials: "Organization admin API key",
    evidence: "Provider-reported costs; excludes Priority Tier",
    component: AnthropicConfig,
    icon: <MdKey className="h-6 w-6" aria-hidden="true" />,
  },
  {
    id: "claude",
    type: "claude",
    name: "Claude subscription",
    description: "Monthly Claude subscription charges from your bills.",
    credentials: "Manual monthly total in USD",
    evidence: "User-entered subscription costs and forecasts",
    component: ClaudeConfig,
    icon: <MdKey className="h-6 w-6" aria-hidden="true" />,
  },
  {
    id: "chatgpt",
    type: "chatgpt",
    name: "ChatGPT subscription",
    description: "Monthly ChatGPT subscription charges from your bills.",
    credentials: "Manual monthly total in USD",
    evidence: "User-entered subscription costs and forecasts",
    component: ChatGPTConfig,
    icon: <MdKey className="h-6 w-6" aria-hidden="true" />,
  },
];

const groups = [
  { name: "AI APIs", types: ["openai", "anthropic"] },
  { name: "AI subscriptions", types: ["claude", "chatgpt"] },
  { name: "Cloud & other tools", types: ["aws", "datadog", "heroku"] },
];
const manual = (type: string) => ["claude", "chatgpt"].includes(type);
interface SelectedSource {
  vendor: VendorConfig;
  config?: { id: number; type: string; identifier: string };
}
export default function APIConfig() {
  const { configurations, loading, error, refresh } = useAPIConfigurations();
  const [selected, setSelected] = useState<SelectedSource | null>(null);
  const dialog = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!selected) return;
    const previous = document.activeElement as HTMLElement | null;
    const oldOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialog.current?.querySelector<HTMLButtonElement>("button")?.focus();
    const keys = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSelected(null);
      if (event.key !== "Tab") return;
      const elements = Array.from(
        dialog.current?.querySelectorAll<HTMLElement>(
          "button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled)"
        ) || []
      );
      const first = elements[0],
        last = elements[elements.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      }
      if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    window.addEventListener("keydown", keys);
    return () => {
      window.removeEventListener("keydown", keys);
      document.body.style.overflow = oldOverflow;
      previous?.focus();
    };
  }, [selected]);
  if (loading) return <p role="status">Loading sources…</p>;
  if (error)
    return (
      <div role="alert">
        <p>{error}</p>
        <button className="is-button-secondary mt-3" onClick={refresh}>
          Retry
        </button>
      </div>
    );
  const count = selected
    ? configurations.filter((c) => c.type === selected.vendor.type).length
    : 0;
  return (
    <>
      <p className="is-muted">
        {configurations.length} configured{" "}
        {configurations.length === 1 ? "account" : "accounts"} · API connections
        and manually maintained bills
      </p>
      {groups.map((group) => (
        <section key={group.name} className="mt-7" aria-label={group.name}>
          <h2 className="mb-3 text-lg font-semibold">{group.name}</h2>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {group.types.map((type) => {
              const vendor = VENDOR_CONFIGS.find((v) => v.type === type)!;
              const accounts = configurations.filter((c) => c.type === type);
              return (
                <div key={type} className="is-panel !p-0">
                  <button
                    className="hover:bg-black/5 w-full rounded-lg p-5 text-left dark:hover:bg-white/5"
                    onClick={() => setSelected({ vendor })}
                  >
                    <h3 className="font-semibold">{vendor.name}</h3>
                    <p className="is-muted mt-2">{vendor.description}</p>
                    <p className="is-muted mt-3">
                      {manual(type)
                        ? "Manually maintained · USD"
                        : vendor.credentials}
                    </p>
                    <span className="mt-4 block font-semibold text-brand-600 dark:text-teal-200">
                      {manual(type)
                        ? "Add monthly bill"
                        : accounts.length
                        ? "Add another account"
                        : "Connect"}{" "}
                      →
                    </span>
                  </button>
                  {accounts.map((account) => (
                    <div
                      key={account.id}
                      className="flex items-center justify-between gap-2 border-t border-gray-200 px-5 py-3 dark:border-white/10"
                    >
                      <Link
                        className="min-w-0 truncate text-sm underline"
                        to={`/admin/vendors/${type}?identifier=${encodeURIComponent(
                          account.identifier
                        )}`}
                      >
                        {account.identifier}
                      </Link>
                      <button
                        className="text-sm font-semibold"
                        onClick={() => setSelected({ vendor, config: account })}
                      >
                        Edit
                      </button>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </section>
      ))}
      {selected && (
        <div
          className="fixed inset-0 z-50 flex justify-end bg-navy-900/70"
          onClick={(e) => {
            if (e.target === e.currentTarget) setSelected(null);
          }}
        >
          <div
            ref={dialog}
            role="dialog"
            aria-modal="true"
            aria-labelledby="source-drawer-title"
            className="h-full w-full max-w-xl overflow-y-auto bg-white p-6 text-navy-700 shadow-2xl dark:bg-navy-800 dark:text-white"
          >
            <div className="mb-6 flex items-start justify-between gap-3">
              <h2 id="source-drawer-title" className="text-2xl font-bold">
                {manual(selected.vendor.type)
                  ? `Add ${selected.vendor.name} bill`
                  : `${selected.config ? "Edit" : "Connect"} ${
                      selected.vendor.name
                    }`}
              </h2>
              <button
                aria-label="Close source setup"
                className="is-button-secondary"
                onClick={() => setSelected(null)}
              >
                <MdClose />
              </button>
            </div>
            {React.createElement(selected.vendor.component, {
              onConfigured: () => {
                refresh();
                setSelected(null);
              },
              existingConfig: Boolean(selected.config),
              initialIdentifier:
                selected.config?.identifier ||
                (count
                  ? `${selected.vendor.name} account ${count + 1}`
                  : "Default Configuration"),
              lockIdentifier: Boolean(selected.config),
            })}
          </div>
        </div>
      )}
    </>
  );
}
