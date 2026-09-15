import { useState, useCallback, useRef } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { CallBackendService } from 'utils';

export interface BudgetEntry {
  month: string;
  amount: number;
}

export interface BudgetPlan {
  id: number;
  vendor: string;
  identifier: string | null;
  user_id: number;
  budgets: { budgets: BudgetEntry[] };
  created_at: string;
  updated_at: string;
  type: string;
}

export const useBudgetPlans = (vendor: string, identifier: string) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [budgetPlan, setBudgetPlan] = useState<BudgetPlan[] | null>(null);
  const [legacyPlans, setLegacyPlans] = useState<BudgetPlan[]>([]);
  const requestId = useRef(0);
  const { getAccessTokenSilently } = useAuth0();

  const fetchBudgetPlan = useCallback(async () => {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError(null);
    setBudgetPlan(null);
    setLegacyPlans([]);
    try {
      const response = await CallBackendService(
        `/v1/budget-plans?vendor=${encodeURIComponent(vendor)}`,
        getAccessTokenSilently,
      );
      if (!Array.isArray(response?.data)) throw new Error('Invalid budget response');
      if (currentRequest === requestId.current) {
        setBudgetPlan(response.data.filter((plan: BudgetPlan) => plan.identifier === identifier));
        setLegacyPlans(response.data.filter((plan: BudgetPlan) => plan.identifier == null));
      }
    } catch (err) {
      if (currentRequest === requestId.current) {
        setError(err instanceof Error ? err.message : 'Failed to fetch budget plan');
      }
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
  }, [vendor, identifier, getAccessTokenSilently]);

  const createBudgetPlan = useCallback(async (budgets: BudgetEntry[]) => {
    setLoading(true);
    setError(null);
    try {
      const response = await CallBackendService('/v1/budget-plans', getAccessTokenSilently, {
        method: 'POST',
        body: JSON.stringify({ vendor, identifier, budgets }),
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response?.data?.id || response.data.identifier !== identifier) {
        throw new Error('Invalid budget save response');
      }
      setBudgetPlan([response.data]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save budget plan');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [vendor, identifier, getAccessTokenSilently]);

  return { loading, error, budgetPlan, legacyPlans, createBudgetPlan, fetchBudgetPlan };
};
