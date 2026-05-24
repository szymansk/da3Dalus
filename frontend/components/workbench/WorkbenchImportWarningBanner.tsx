"use client";

import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import ImportWarningBanner from "@/components/workbench/ImportWarningBanner";

/**
 * Context-aware wrapper around ``ImportWarningBanner`` (gh-695).
 *
 * Renders the banner only when:
 * 1. A recent OpenVSP import has captured warnings into context.
 * 2. The currently-selected aeroplane is the one those warnings
 *    belong to (switching away hides the banner — the user is no
 *    longer looking at that aeroplane).
 *
 * Per-aeroplane dismiss is handled by ``ImportWarningBanner`` itself
 * via localStorage.
 */
export function WorkbenchImportWarningBanner() {
  const { lastImportWarnings, aeroplaneId } = useAeroplaneContext();

  if (!lastImportWarnings) return null;
  if (lastImportWarnings.uuid !== aeroplaneId) return null;
  if (lastImportWarnings.warnings.length === 0) return null;

  return (
    <ImportWarningBanner
      warnings={lastImportWarnings.warnings}
      aeroplaneUuid={lastImportWarnings.uuid}
    />
  );
}
