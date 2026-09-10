import React, { useEffect, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { CallBackendService } from "utils";

export interface BillingConfigProps {
  onConfigured?: () => void;
  existingConfig?: boolean;
  initialIdentifier?: string;
  lockIdentifier?: boolean;
}
interface Charge {
  month: string;
  cost: number;
}
const labels = {
  openai: "OpenAI API",
  anthropic: "Claude API (Anthropic)",
  claude: "Claude subscription",
  chatgpt: "ChatGPT subscription",
};
type Provider = keyof typeof labels;

const AIBillingConfig: React.FC<
  BillingConfigProps & { provider: Provider }
> = ({
  provider,
  onConfigured,
  existingConfig,
  initialIdentifier = "Default Configuration",
  lockIdentifier,
}) => {
  const { getAccessTokenSilently } = useAuth0();
  const [identifier, setIdentifier] = useState(initialIdentifier);
  const [apiKey, setApiKey] = useState("");
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));
  const [cost, setCost] = useState("");
  const [charges, setCharges] = useState<Charge[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const manual = provider === "claude" || provider === "chatgpt";
  const label = labels[provider];
  const monthKey = (value: string) => `${value.slice(5)}-${value.slice(0, 4)}`;
  const inputClass =
    "mt-2 w-full rounded-md border border-gray-200 bg-transparent p-3 text-sm dark:border-white/10 dark:text-white";

  useEffect(() => {
    if (!manual || !existingConfig) return;
    let active = true;
    setLoading(true);
    CallBackendService(
      `/v1/vendors-metrics/${provider}?identifier=${encodeURIComponent(
        initialIdentifier
      )}`,
      getAccessTokenSilently
    )
      .then((response: { data: Charge[] }) => {
        if (active) setCharges(response.data);
      })
      .catch(() => {
        if (active)
          setError(
            "Unable to load saved monthly charges. Close and reopen to retry."
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [
    manual,
    existingConfig,
    provider,
    initialIdentifier,
    getAccessTokenSilently,
  ]);

  useEffect(() => {
    const saved = charges.find((charge) => charge.month === monthKey(month));
    setCost(saved ? String(saved.cost) : "");
  }, [charges, month]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await CallBackendService(
        `/v1/configuration/${manual ? "subscriptions" : "ai"}/${provider}`,
        getAccessTokenSilently,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(
            manual
              ? {
                  identifier: identifier.trim(),
                  month: monthKey(month),
                  cost,
                  currency: "USD",
                }
              : { identifier: identifier.trim(), api_key: apiKey.trim() }
          ),
        }
      );
      setApiKey("");
      onConfigured?.();
    } catch {
      setError(`Unable to save ${label}. Check the values and try again.`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form
      onSubmit={submit}
      className="space-y-5 text-sm text-gray-700 dark:text-gray-300"
    >
      <p>
        {manual
          ? "Enter the monthly total from your subscription bill in USD, including tax if charged. Each saved month is a manual entry; missing months remain unknown. Saving an existing month replaces its total."
          : "Import organization-wide API billing with an organization admin API key. Subscription charges are entered separately. Credentials are stored in the existing secret manager."}
      </p>
      {!manual && (
        <p>
          {provider === "anthropic"
            ? "Use a Claude Console organization Admin API key. This report excludes Priority Tier costs and is unavailable for individual accounts."
            : "Use an OpenAI organization Admin API key with permission to read costs; a project inference key is insufficient."}
        </p>
      )}
      <label className="block">
        Account name
        <input
          aria-label="Account name"
          required
          maxLength={200}
          readOnly={lockIdentifier}
          value={identifier}
          onChange={(event) => setIdentifier(event.target.value)}
          className={inputClass}
        />
      </label>
      {manual ? (
        <>
          <label className="block">
            Billing month
            <input
              aria-label="Billing month"
              type="month"
              required
              max={new Date().toISOString().slice(0, 7)}
              value={month}
              onChange={(event) => setMonth(event.target.value)}
              className={inputClass}
            />
          </label>
          <label className="block">
            Monthly total (USD)
            <input
              aria-label="Monthly total (USD)"
              type="number"
              required
              min="0"
              max="9999999999.99"
              step="0.01"
              value={cost}
              onChange={(event) => setCost(event.target.value)}
              className={inputClass}
            />
          </label>
          {charges.length > 0 && (
            <p>
              Saved months:{" "}
              {charges
                .map((charge) => `${charge.month}: $${charge.cost.toFixed(2)}`)
                .join(" · ")}
            </p>
          )}
        </>
      ) : (
        <label className="block">
          Organization admin API key
          <input
            aria-label="Organization admin API key"
            type="password"
            autoComplete="new-password"
            required
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            className={inputClass}
          />
        </label>
      )}
      {error && (
        <p role="alert" className="text-red-600 dark:text-red-300">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-md bg-brand-500 px-4 py-3 font-semibold text-white disabled:opacity-50"
      >
        {loading
          ? "Saving..."
          : manual
          ? "Save monthly total"
          : "Save API credentials"}
      </button>
    </form>
  );
};
export const OpenAIConfig = (props: BillingConfigProps) => (
  <AIBillingConfig {...props} provider="openai" />
);
export const AnthropicConfig = (props: BillingConfigProps) => (
  <AIBillingConfig {...props} provider="anthropic" />
);
export const ClaudeConfig = (props: BillingConfigProps) => (
  <AIBillingConfig {...props} provider="claude" />
);
export const ChatGPTConfig = (props: BillingConfigProps) => (
  <AIBillingConfig {...props} provider="chatgpt" />
);
