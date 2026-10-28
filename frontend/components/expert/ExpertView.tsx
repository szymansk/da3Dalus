"use client";

import { useState } from "react";
import { useCanonFleet } from "@/hooks/useCanonFleet";
import { API_BASE } from "@/lib/fetcher";
import { canonNavigatorUrl } from "@/lib/canonNavigator";

/**
 * Expert View (gh-1282, ADR 0030): the canon navigator connected to the kernel.
 *
 * A development view for experts. The kernel's values stand beside the app's own and are never
 * written back. The graph is the generated navigator page, hosted in a frame.
 */
export function ExpertView() {
  const { fleet, error, isLoading } = useCanonFleet();
  const [chosen, setChosen] = useState<string | null>(null);
  const aircraftId = chosen ?? fleet[0]?.id ?? null;
  const aircraft = fleet.find((a) => a.id === aircraftId);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <div className="flex flex-wrap items-center gap-4">
        <span
          role="note"
          className="rounded-full border border-primary/50 bg-primary/10 px-3 py-1 text-[12px] font-medium text-primary"
        >
          Canon/kernel view (development), experts only
        </span>
        <label className="flex items-center gap-2 text-[13px] text-muted-foreground">
          <span>Aircraft</span>
          <select
            aria-label="Aircraft"
            value={aircraftId ?? ""}
            onChange={(event) => setChosen(event.target.value)}
            disabled={fleet.length === 0}
            className="rounded-md border border-border bg-card-muted px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground"
          >
            {fleet.map((entry) => (
              <option key={entry.id} value={entry.id}>
                {entry.name}
              </option>
            ))}
          </select>
        </label>
        {aircraft && (
          <span className="text-[12px] text-muted-foreground">
            {aircraft.mass_kg} kg
          </span>
        )}
      </div>

      {isLoading && (
        <p className="text-[13px] text-muted-foreground">Loading the fleet&hellip;</p>
      )}
      {error && (
        <p role="alert" className="text-[13px] text-red-400">
          The fleet could not be loaded: {String(error.message ?? error)}
        </p>
      )}
      {aircraftId && (
        <iframe
          key={aircraftId}
          title="Canon navigator, connected to the kernel"
          src={canonNavigatorUrl(API_BASE, aircraftId)}
          className="min-h-0 flex-1 rounded-lg border border-border bg-background"
        />
      )}
    </div>
  );
}
