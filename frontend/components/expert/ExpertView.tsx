"use client";

import { useState } from "react";
import { useCanonAircraft } from "@/hooks/useCanonAircraft";
import { API_BASE } from "@/lib/fetcher";
import { canonNavigatorUrl } from "@/lib/canonNavigator";
import type { CanonAircraftRef } from "@/types/canon";

/** One entry of the picker: the reference the navigator computes with and the mass it shows. */
interface Choice {
  key: string;
  ref: CanonAircraftRef;
  name: string;
  massText: string;
}

const FLEET_GROUP = "Reference fleet";
const STORED_GROUP = "Stored aeroplanes";

/**
 * Expert View (gh-1282, ADR 0030): the canon navigator connected to the kernel.
 *
 * A development view for experts. The kernel's values stand beside the app's own and are never
 * written back. The graph is the generated navigator page, hosted in a frame. The picker offers the
 * kernel's reference fleet and, separately, the stored aeroplanes in their current state.
 */
export function ExpertView() {
  const { fleet, aeroplanes, error, isLoading } = useCanonAircraft();
  const [chosen, setChosen] = useState<string | null>(null);

  const fleetChoices: Choice[] = fleet.map((entry) => ({
    key: `fleet:${entry.id}`,
    ref: { fleet: entry.id },
    name: entry.name,
    massText: `${entry.mass_kg} kg`,
  }));
  const storedChoices: Choice[] = aeroplanes.map((entry) => ({
    key: `aeroplane:${entry.id}`,
    ref: { aeroplane: entry.id },
    name: entry.name,
    massText: entry.mass_kg === null ? "mass not set" : `${entry.mass_kg} kg (mass assumption)`,
  }));
  const choices = [...fleetChoices, ...storedChoices];
  const current = choices.find((c) => c.key === chosen) ?? choices[0];

  const groups: [string, Choice[]][] = [
    [FLEET_GROUP, fleetChoices],
    [STORED_GROUP, storedChoices],
  ];

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
            value={current?.key ?? ""}
            onChange={(event) => setChosen(event.target.value)}
            disabled={choices.length === 0}
            className="rounded-md border border-border bg-card-muted px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground"
          >
            {groups
              .filter(([, members]) => members.length > 0)
              .map(([label, members]) => (
                <optgroup key={label} label={label}>
                  {members.map((choice) => (
                    <option key={choice.key} value={choice.key}>
                      {choice.name}
                    </option>
                  ))}
                </optgroup>
              ))}
          </select>
        </label>
        {current && (
          <span className="text-[12px] text-muted-foreground">{current.massText}</span>
        )}
      </div>

      {isLoading && (
        <p className="text-[13px] text-muted-foreground">Loading the aircraft&hellip;</p>
      )}
      {error && (
        <p role="alert" className="text-[13px] text-red-400">
          The aircraft could not be loaded: {String(error.message ?? error)}
        </p>
      )}
      {current && (
        <iframe
          key={current.key}
          title="Canon navigator, connected to the kernel"
          src={canonNavigatorUrl(API_BASE, current.ref)}
          className="min-h-0 flex-1 rounded-lg border border-border bg-background"
        />
      )}
    </div>
  );
}
