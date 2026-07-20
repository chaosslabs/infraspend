import { useEffect } from "react";
import { Link } from "react-router-dom";
import VendorMetrics from "./components/VendorMetrics";
import { useAPIConfigurations } from "./components/hooks/useAPIConfigurations";
import { LoadingState } from "components/loading/LoadingState";

const VENDOR_TITLES: Record<string, string> = {
  datadog: "Datadog Metrics",
  aws: "AWS Metrics",
  heroku: "Heroku Metrics",
};

const Dashboard = () => {
  const { configurations, loading } = useAPIConfigurations();
  
  useEffect(() => {
    document.title = "Dashboard";
  }, []);

  if (loading) {
    return <LoadingState />;
  }

  if (configurations.length === 0) {
    return (
      <div className="mt-3 flex flex-col items-center justify-center">
        <h1 className="text-2xl font-bold text-navy-700 dark:text-white">
          Welcome to InfraSpend 🚀
        </h1>
        <p className="mt-4 text-gray-600 dark:text-gray-400">
          To get started, you'll need to configure some accounts.
        </p>
        <Link
          to="/admin/linked-accounts"
          className="mt-6 rounded-xl bg-brand-500 px-6 py-3 text-white hover:bg-brand-600"
        >
          let's get to it!
        </Link>
      </div>
    );
  }

  return (
    <div className="mt-3">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {configurations.map((config) => {
          const title = VENDOR_TITLES[config.type];
          if (!title) return null;

          return (
            <VendorMetrics
              key={`${config.type}-${config.id}`}
              identifier={config.identifier}
              vendor={config.type as "datadog" | "aws" | "heroku"}
              title={title}
            />
          );
        })}
      </div>
    </div>
  );
};

export default Dashboard;
