"use client";

import { useState } from "react";
import type {
  TrimEnrichment,
  DesignWarning,
} from "@/hooks/useOperatingPoints";

const WARNING_STYLES = {
  info: "border-blue-500/30 bg-blue-500/10 text-blue-400",
  warning: "border-yellow-500/30 bg-yellow-500/10 text-yellow-400",
  critical: "border-red-500/30 bg-red-500/10 text-red-400",
} as const;

const DETAIL_BG = {
  info: "bg-blue-500/5",
  warning: "bg-yellow-500/5",
  critical: "bg-red-500/5",
} as const;

function displaySurfaceName(encoded: string): string {
  const match = encoded.match(/^\[(\w+)\](.+)$/);
  return match ? match[2] : encoded;
}

function WarningBadge({
  warning,
  index,
  isExpanded,
  onToggle,
}: {
  warning: DesignWarning;
  index: number;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="flex flex-col">
      <button
        type="button"
        onClick={onToggle}
        className={`cursor-pointer rounded-lg border px-3 py-2 text-left transition-all ${WARNING_STYLES[warning.level] ?? WARNING_STYLES.info}`}
      >
        <span className="font-[family-name:var(--font-geist-sans)] text-[12px]">
          {warning.message}
        </span>
      </button>
      {isExpanded && (
        <div
          data-testid={`warning-detail-${index}`}
          className={`mt-1 rounded-b-lg px-3 py-2 ${DETAIL_BG[warning.level] ?? DETAIL_BG.info}`}
        >
          <dl className="flex flex-col gap-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
            <div className="flex gap-2">
              <dt className="font-medium">Category:</dt>
              <dd>{warning.category}</dd>
            </div>
            {warning.surface && (
              <div className="flex gap-2">
                <dt className="font-medium">Surface:</dt>
                <dd>{displaySurfaceName(warning.surface)}</dd>
              </div>
            )}
            <div className="flex gap-2">
              <dt className="font-medium">Severity:</dt>
              <dd className="capitalize">{warning.level}</dd>
            </div>
          </dl>
        </div>
      )}
    </div>
  );
}

interface Props {
  readonly enrichment: TrimEnrichment | null;
}

export function DesignWarningBadges({ enrichment }: Props) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  if (!enrichment || enrichment.design_warnings.length === 0) return null;

  return (
    <div className="flex flex-col gap-1.5">
      {enrichment.design_warnings.map((w, i) => (
        <WarningBadge
          key={i}
          warning={w}
          index={i}
          isExpanded={expandedIndex === i}
          onToggle={() => setExpandedIndex(expandedIndex === i ? null : i)}
        />
      ))}
    </div>
  );
}
