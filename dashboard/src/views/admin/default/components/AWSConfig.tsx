import React, { useEffect, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { CallBackendService } from "utils";

interface AWSConfigProps {
  onConfigured?: () => void;
  existingConfig?: boolean;
  initialIdentifier?: string;
  lockIdentifier?: boolean;
}

const AWSConfig: React.FC<AWSConfigProps> = ({
  onConfigured,
  existingConfig,
  initialIdentifier = "Default Configuration",
  lockIdentifier,
}) => {
  const [accessKeyId, setAccessKeyId] = useState("");
  const [secretAccessKey, setSecretAccessKey] = useState("");
  const [identifier, setIdentifier] = useState(initialIdentifier);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const { getAccessTokenSilently } = useAuth0();

  useEffect(() => {
    setIdentifier(initialIdentifier);
  }, [initialIdentifier]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      await CallBackendService(
        "/v1/configuration/aws",
        getAccessTokenSilently,
        {
          method: "POST",
          body: JSON.stringify({
            aws_access_key_id: accessKeyId,
            aws_secret_access_key: secretAccessKey,
            identifier: identifier
          }),
          headers: { "Content-Type": "application/json" },
        }
      );

      setSuccess(existingConfig 
        ? "AWS credentials updated successfully!" 
        : "AWS credentials configured successfully!");
      setAccessKeyId("");
      setSecretAccessKey("");
      
      if (onConfigured) {
        onConfigured();
      }
    } catch (error: any) {
      setError(error.message || "Failed to configure AWS credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="relative flex flex-row justify-between">
        <div className="flex items-center">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-brand-50 text-brand-600 ring-1 ring-brand-100 dark:bg-brand-500/10 dark:text-teal-200 dark:ring-brand-400/20">
            <svg
              className="h-6 w-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"
              />
            </svg>
          </div>
          <h5 className="ml-4 text-lg font-bold text-navy-700 dark:text-white">
            AWS Configuration
          </h5>
        </div>
      </div>

      <div className="mt-8 w-full">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex flex-col">
            <label
              htmlFor="aws-access-key-id"
              className="mb-2 text-sm font-medium text-gray-900 dark:text-white"
            >
              AWS Access Key ID
            </label>
            <input
              id="aws-access-key-id"
              type="text"
              value={accessKeyId}
              onChange={(e) => setAccessKeyId(e.target.value)}
              className="mt-2 flex h-12 w-full items-center justify-center rounded-md border border-gray-200 bg-white/0 p-3 text-sm outline-none dark:!border-white/10 dark:text-white"
              placeholder="Enter AWS Access Key ID"
              required
            />
          </div>

          <div className="flex flex-col">
            <label
              htmlFor="aws-secret-access-key"
              className="mb-2 text-sm font-medium text-gray-900 dark:text-white"
            >
              AWS Secret Access Key
            </label>
            <input
              id="aws-secret-access-key"
              type="password"
              value={secretAccessKey}
              onChange={(e) => setSecretAccessKey(e.target.value)}
              className="mt-2 flex h-12 w-full items-center justify-center rounded-md border border-gray-200 bg-white/0 p-3 text-sm outline-none dark:!border-white/10 dark:text-white"
              placeholder="Enter AWS Secret Access Key"
              required
            />
          </div>

          <div className="flex flex-col">
            <label
              htmlFor="aws-configuration-name"
              className="mb-2 text-sm font-medium text-gray-900 dark:text-white"
            >
              Configuration Name
            </label>
            <input
              id="aws-configuration-name"
              type="text"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              readOnly={lockIdentifier}
              className={`mt-2 flex h-12 w-full items-center justify-center rounded-md border border-gray-200 bg-white/0 p-3 text-sm outline-none dark:!border-white/10 dark:text-white ${
                lockIdentifier ? "cursor-not-allowed bg-gray-100/50 dark:bg-white/5" : ""
              }`}
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
            className={`linear mt-4 w-full rounded-md bg-brand-500 px-4 py-3 text-base font-medium text-white transition duration-200 hover:bg-brand-600 active:bg-brand-700 dark:bg-brand-400 dark:text-white dark:hover:bg-brand-300 dark:active:bg-brand-200 ${
              loading ? "cursor-not-allowed opacity-50" : ""
            }`}
          >
            {loading ? "Configuring..." : existingConfig ? "Update AWS" : "Configure AWS"}
          </button>
        </form>
      </div>
    </div>
  );
};

export default AWSConfig;
