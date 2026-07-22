import { useEffect } from "react";
import APIConfig from "../default/components/APIConfig";

export default function Configuration() {
  useEffect(() => {
    document.title = "Linked Accounts";
  }, []);

  return (
    <div className="mx-auto mt-3 max-w-[1500px] space-y-6">
      <div>
        <p className="text-sm font-semibold uppercase text-brand-600 dark:text-teal-200">
          Linked accounts
        </p>
        <h1 className="mt-2 text-3xl font-bold leading-tight text-navy-700 dark:text-white">
          Linked cost sources
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-700 dark:text-gray-300">
          Manage the read-only provider credentials that power InfraSpend cost
          evidence, source freshness, forecasts, and budget planning.
        </p>
      </div>
      <APIConfig />
    </div>
  );
}
