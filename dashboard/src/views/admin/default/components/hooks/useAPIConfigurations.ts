import { useState, useEffect } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { CallBackendService } from "utils";

interface APIConfiguration {
  id: number;
  type: string;
  identifier: string;
}

export const useAPIConfigurations = () => {
  const [configurations, setConfigurations] = useState<APIConfiguration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { getAccessTokenSilently } = useAuth0();

  const fetchConfigurations = async () => {
    try {
      setLoading(true);
      const response = await CallBackendService(
        "/v1/configuration/list",
        getAccessTokenSilently
      );
      setConfigurations(response.data || []);
      setError(null);
    } catch (error: any) {
      setError(error.message || "Failed to fetch configurations");
      setConfigurations([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfigurations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [getAccessTokenSilently]);

  return { configurations, loading, error, refresh: fetchConfigurations };
}; 