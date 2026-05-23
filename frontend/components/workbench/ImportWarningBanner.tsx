"use client";

import { useState } from "react";

import type { ImportOpenVspWarning } from "./ImportOpenVspButton";

/**
 * Warning banner for the OpenVSP `.vsp3` importer (gh-648).
 *
 * Renders the list of warnings produced by /api/v2/import/openvsp.
 * Dismissible per-aeroplane via localStorage so the user isn't
 * pestered after they've acknowledged the import losses.
 *
 * Severity styling:
 * * error   → red border + heavy weight
 * * warning → orange border (project accent #FF8400)
 * * info    → neutral border, less prominent
 */

type Props = {
  warnings: ImportOpenVspWarning[];
  aeroplaneUuid: string;
  className?: string;
};

const STORAGE_PREFIX = "vsp-warnings-dismissed-";

function pickHighestSeverity(
  warnings: ImportOpenVspWarning[],
): ImportOpenVspWarning["severity"] {
  if (warnings.some((w) => w.severity === "error")) return "error";
  if (warnings.some((w) => w.severity === "warning")) return "warning";
  return "info";
}

const severityStyles: Record<
  ImportOpenVspWarning["severity"],
  { border: string; badge: string; label: string }
> = {
  error: {
    border: "border-red-500",
    badge: "bg-red-700 text-white",
    label: "ERROR",
  },
  warning: {
    border: "border-[#FF8400]",
    badge: "bg-[#FF8400] text-black",
    label: "WARNING",
  },
  info: {
    border: "border-neutral-600",
    badge: "bg-neutral-700 text-neutral-200",
    label: "INFO",
  },
};

export default function ImportWarningBanner({
  warnings,
  aeroplaneUuid,
  className = "",
}: Props) {
  const storageKey = `${STORAGE_PREFIX}${aeroplaneUuid}`;
  // Lazy initialiser reads localStorage exactly once during mount —
  // this avoids the "setState in effect" lint rule that fires on
  // post-mount sync calls.
  const [dismissed, setDismissed] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    try {
      return window.localStorage.getItem(storageKey) === "true";
    } catch {
      return false;
    }
  });

  function dismiss() {
    setDismissed(true);
    try {
      window.localStorage.setItem(storageKey, "true");
    } catch {
      // Best-effort persistence; the banner stays dismissed in-session.
    }
  }

  if (dismissed || warnings.length === 0) {
    return null;
  }

  // Pick the highest severity to colour the outer frame.
  const highestSeverity: ImportOpenVspWarning["severity"] = pickHighestSeverity(warnings);
  const frame = severityStyles[highestSeverity];

  return (
    <div
      role="alert"
      data-testid="openvsp-warning-banner"
      className={`mb-4 rounded-md border-2 ${frame.border} bg-neutral-900 p-3 text-sm text-neutral-100 ${className}`}
    >
      <div className="mb-2 flex items-start justify-between gap-3">
        <h3 className="font-semibold text-neutral-100">
          {warnings.length === 1
            ? "1 component was not fully imported"
            : `${warnings.length} components were not fully imported`}
        </h3>
        <button
          type="button"
          onClick={dismiss}
          className="rounded px-2 py-0.5 text-xs text-neutral-400 hover:bg-neutral-800 hover:text-neutral-100"
          data-testid="openvsp-warning-dismiss"
          aria-label="Dismiss import warnings"
        >
          Dismiss
        </button>
      </div>
      <ul className="space-y-1.5">
        {warnings.map((w, i) => {
          const sty = severityStyles[w.severity];
          return (
            <li
              key={`${w.component_type}-${w.component_name}-${i}`}
              className="flex items-start gap-2"
            >
              <span
                className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${sty.badge}`}
              >
                {sty.label}
              </span>
              <span className="text-neutral-200">
                <span className="font-medium">{w.component_type}</span>{" "}
                <span className="text-neutral-400">
                  &ldquo;{w.component_name}&rdquo;
                </span>
                : <span>{w.reason}</span>
              </span>
            </li>
          );
        })}
      </ul>
      <p className="mt-2 text-xs text-neutral-500">
        Some OpenVSP features are intentionally out of scope for the
        Phase 1 RC-scaling importer. Edit any imported component in the
        workbench to refine the model.
      </p>
    </div>
  );
}
