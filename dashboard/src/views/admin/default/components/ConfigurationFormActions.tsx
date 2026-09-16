import React from "react";

interface ConfigurationFormActionsProps {
  provider: string;
  loading: boolean;
  existingConfig?: boolean;
  error: string | null;
  success: string | null;
}

export default function ConfigurationFormActions({
  provider,
  loading,
  existingConfig,
  error,
  success,
}: ConfigurationFormActionsProps) {
  const action = existingConfig ? "Update" : "Configure";
  const label = loading ? "Configuring..." : `${action} ${provider}`;

  return (
    <>
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
        {label}
      </button>
    </>
  );
}
