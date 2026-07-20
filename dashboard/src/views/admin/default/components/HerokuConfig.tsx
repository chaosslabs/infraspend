import Card from "components/card";
import React, { useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { CallBackendService } from "utils";

interface HerokuConfigProps {
  onConfigured?: () => void;
  existingConfig?: boolean;
}

const HerokuConfig: React.FC<HerokuConfigProps> = ({
  onConfigured,
  existingConfig,
}) => {
  const [apiKey, setApiKey] = useState("");
  const [teamNameOrId, setTeamNameOrId] = useState("");
  const [identifier, setIdentifier] = useState("Default Configuration");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const { getAccessTokenSilently } = useAuth0();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      await CallBackendService(
        "/v1/configuration/heroku",
        getAccessTokenSilently,
        {
          method: "POST",
          body: JSON.stringify({
            api_key: apiKey,
            team_name_or_id: teamNameOrId.trim() || null,
            identifier,
          }),
          headers: { "Content-Type": "application/json" },
        }
      );

      setSuccess(
        existingConfig
          ? "Heroku credentials updated successfully!"
          : "Heroku credentials configured successfully!"
      );
      setApiKey("");
      setTeamNameOrId("");

      if (onConfigured) {
        onConfigured();
      }
    } catch (error: any) {
      setError(error.message || "Failed to configure Heroku credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card extra="!p-[20px] text-center">
      <div className="relative flex flex-row justify-between">
        <div className="flex items-center">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-100 dark:bg-white/5">
            <svg
              className="h-6 w-6 text-brand-500 dark:text-white"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M20.61 0H3.39C2.16 0 1.16 1 1.16 2.23v19.54C1.16 23 2.16 24 3.39 24h17.22c1.23 0 2.23-1 2.23-2.23V2.23C22.84 1 21.84 0 20.61 0zM19 20.34h-3.03v-6.9c0-.62-.18-1.06-.54-1.32-.36-.26-.91-.39-1.64-.39-.52 0-1.02.07-1.5.2-.48.13-.91.3-1.29.5v7.91H7.97V3.63H11v5.76c.43-.22.91-.39 1.45-.52.54-.13 1.13-.19 1.77-.19 1.52 0 2.7.36 3.54 1.08.83.72 1.25 1.83 1.25 3.34v7.24H19zM6.45 20.34H3.42V3.63h3.03v16.71z" />
            </svg>
          </div>
          <h5 className="ml-4 text-lg font-bold text-navy-700 dark:text-white">
            Heroku Configuration
          </h5>
        </div>
      </div>

      <div className="mt-8 w-full">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex flex-col">
            <label className="mb-2 text-sm font-medium text-gray-900 dark:text-white">
              Heroku API Key
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="mt-2 flex h-12 w-full items-center justify-center rounded-xl border bg-white/0 p-3 text-sm outline-none border-gray-200 dark:!border-white/10 dark:text-white"
              placeholder="Enter Heroku API key"
              required
            />
          </div>

          <div className="flex flex-col">
            <label className="mb-2 text-sm font-medium text-gray-900 dark:text-white">
              Team Name or ID
            </label>
            <input
              type="text"
              value={teamNameOrId}
              onChange={(e) => setTeamNameOrId(e.target.value)}
              className="mt-2 flex h-12 w-full items-center justify-center rounded-xl border bg-white/0 p-3 text-sm outline-none border-gray-200 dark:!border-white/10 dark:text-white"
              placeholder="Leave blank for personal account invoices"
            />
          </div>

          <div className="flex flex-col">
            <label className="mb-2 text-sm font-medium text-gray-900 dark:text-white">
              Configuration Name
            </label>
            <input
              type="text"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              className="mt-2 flex h-12 w-full items-center justify-center rounded-xl border bg-white/0 p-3 text-sm outline-none border-gray-200 dark:!border-white/10 dark:text-white"
              placeholder="Enter configuration name"
              required
            />
          </div>

          {error && (
            <div className="mt-4 rounded-lg bg-red-50 p-4 text-sm text-red-500 dark:bg-red-900/20">
              {error}
            </div>
          )}

          {success && (
            <div className="mt-4 rounded-lg bg-green-50 p-4 text-sm text-green-500 dark:bg-green-900/20">
              {success}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className={`linear mt-4 w-full rounded-xl bg-brand-500 px-4 py-3 text-base font-medium text-white transition duration-200 hover:bg-brand-600 active:bg-brand-700 dark:bg-brand-400 dark:text-white dark:hover:bg-brand-300 dark:active:bg-brand-200 ${
              loading ? "cursor-not-allowed opacity-50" : ""
            }`}
          >
            {loading
              ? "Configuring..."
              : existingConfig
              ? "Update Heroku"
              : "Configure Heroku"}
          </button>
        </form>
      </div>
    </Card>
  );
};

export default HerokuConfig;
