export const DEFAULT_RETURN_TO = "/admin/default";

// Only restore routes inside the private workspace, never external URLs.
export function safeReturnTo(value: unknown): string {
  if (typeof value !== "string") return DEFAULT_RETURN_TO;
  try {
    const url = new URL(value, window.location.origin);
    if (url.origin === window.location.origin && url.pathname.startsWith("/admin/")) {
      return `${url.pathname}${url.search}${url.hash}`;
    }
  } catch {
    // Invalid destinations fall back to the workspace home.
  }
  return DEFAULT_RETURN_TO;
}
