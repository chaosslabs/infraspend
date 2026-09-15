const getBackendUrl = (): string => {
  return process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
};

export const CallBackendService = async (
  path: string,
  getAccessTokenSilently: () => Promise<string>,
  options: RequestInit = {},
): Promise<any> => {
  const token = await getAccessTokenSilently();
  const response = await fetch(getBackendUrl() + path, {
    ...options,
    headers: { Authorization: `Bearer ${token}`, ...options.headers },
  });
  if (response.status === 204) return null;
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((entry: { msg?: string }) => entry.msg).filter(Boolean).join('; ')
        : payload?.message || detail?.message;
    throw new Error(message || `Request failed (${response.status})`);
  }
  if (payload === null) throw new Error('The server returned an invalid response');
  return payload;
};
