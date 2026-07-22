import React from "react";
import {
  MdCheckCircle,
  MdError,
  MdHelpOutline,
  MdSync,
  MdWarningAmber,
} from "react-icons/md";

/**
 * Source-health / freshness surfacing for vendor cost metrics.
 *
 * Trust is the product wedge: cached, stale, partial, or failed source data
 * must never look silently current. This module turns the (additive) ingestion
 * fields returned by the metrics API into a small, explicit, colour-independent
 * badge. When the API has not yet been extended with these fields, the state
 * degrades to an explicit "unknown" rather than implying freshness.
 */

// Ingestion outcome as reported by the backend for the latest attempt.
export type IngestionStatus = "success" | "partial" | "failed";

// Additive freshness fields on the vendor-metrics response. All optional so the
// dashboard stays compatible with API versions that do not yet return them.
export interface SourceHealthFields {
  last_success_at?: string | null; // ISO timestamp of last fully successful ingestion
  last_attempt_at?: string | null; // ISO timestamp of latest ingestion attempt
  last_attempt_status?: IngestionStatus | null;
  data_through?: string | null; // period the data is complete through, e.g. "07-2026"
  record_count?: number | null; // number of stored monthly records
  stale_after_hours?: number | null; // freshness threshold supplied by the API
}

export type HealthState =
  | "unknown" // no ingestion evidence available
  | "never" // never successfully ingested
  | "failed" // latest attempt failed; any data shown is cached
  | "partial" // latest attempt only partially refreshed
  | "stale" // last success older than the freshness threshold
  | "fresh"; // recent successful ingestion

export interface SourceHealthResult {
  state: HealthState;
  label: string; // short, human-readable state
  detail: string; // supporting timestamp/context
}

/**
 * Freshness threshold. Data whose last successful ingestion is older than this
 * is surfaced as "Stale". Named and documented here rather than hidden in UI
 * copy; the backend refreshes the current month once its data is older than a
 * day, so 48h gives one full refresh cycle of tolerance before we flag it.
 */
export const STALE_AFTER_HOURS = 48;

export function formatRelativeTime(
  iso: string | null | undefined,
  now: number = Date.now()
): string {
  if (!iso) return "unknown";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "unknown";
  const diffMs = now - then;
  if (diffMs < 0) return "just now";
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  return `${days}d ago`;
}

/**
 * Pure derivation of a health state from the response fields. Order matters:
 * a failed or partial latest attempt takes precedence over the age of the last
 * success, so cached data after a failed refresh is never labelled "fresh".
 */
export function deriveSourceHealth(
  fields: SourceHealthFields | null | undefined,
  now: number = Date.now()
): SourceHealthResult {
  const f = fields ?? {};
  const hasSignal =
    f.last_success_at != null ||
    f.last_attempt_at != null ||
    f.last_attempt_status != null;

  if (!hasSignal) {
    return {
      state: "unknown",
      label: "Freshness unknown",
      detail: "no ingestion data reported",
    };
  }

  if (!f.last_success_at) {
    return {
      state: "never",
      label: "Never synced",
      detail: f.last_attempt_at
        ? `last attempt ${formatRelativeTime(f.last_attempt_at, now)}`
        : "no successful ingestion yet",
    };
  }

  const lastSuccess = formatRelativeTime(f.last_success_at, now);

  if (f.last_attempt_status === "failed") {
    return {
      state: "failed",
      label: "Cached - refresh failed",
      detail: `last success ${lastSuccess}`,
    };
  }

  if (f.last_attempt_status === "partial") {
    return {
      state: "partial",
      label: "Partial refresh",
      detail: `last success ${lastSuccess}`,
    };
  }

  const staleAfter =
    f.stale_after_hours != null && f.stale_after_hours > 0
      ? f.stale_after_hours
      : STALE_AFTER_HOURS;
  const ageHours = (now - new Date(f.last_success_at).getTime()) / 3_600_000;
  if (ageHours > staleAfter) {
    return {
      state: "stale",
      label: "Stale",
      detail: `last success ${lastSuccess}`,
    };
  }

  return {
    state: "fresh",
    label: "Fresh",
    detail: `updated ${lastSuccess}`,
  };
}

const STATE_STYLES: Record<
  HealthState,
  { className: string; Icon: React.ComponentType<{ className?: string }> }
> = {
  fresh: {
    className:
      "bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300",
    Icon: MdCheckCircle,
  },
  stale: {
    className:
      "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300",
    Icon: MdWarningAmber,
  },
  partial: {
    className:
      "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300",
    Icon: MdSync,
  },
  failed: {
    className: "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300",
    Icon: MdError,
  },
  never: {
    className: "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300",
    Icon: MdError,
  },
  unknown: {
    className:
      "bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-gray-300",
    Icon: MdHelpOutline,
  },
};

/**
 * Compact freshness badge. Conveys state through icon + text as well as colour
 * so it remains legible without relying on colour alone (accessibility).
 */
export const SourceHealthBadge: React.FC<{ health: SourceHealthResult }> = ({
  health,
}) => {
  const { className, Icon } = STATE_STYLES[health.state];
  return (
    <span
      role="status"
      aria-label={`Source data: ${health.label}, ${health.detail}`}
      title={`${health.label} · ${health.detail}`}
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-1 text-xs font-semibold ${className}`}
    >
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      <span>{health.label}</span>
      <span className="font-normal opacity-80">· {health.detail}</span>
    </span>
  );
};

export default SourceHealthBadge;
