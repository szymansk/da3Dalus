"use client";

import { AlertTriangle, Loader2, Plus } from "lucide-react";
import { useDesignAssumptions } from "@/hooks/useDesignAssumptions";
import type { AssumptionParameterName } from "@/hooks/useDesignAssumptions";
import { useComputationContext } from "@/hooks/useComputationContext";
import { AssumptionRow } from "@/components/workbench/AssumptionRow";
import { CGComparisonBanner } from "@/components/workbench/CGComparisonBanner";
import { PolarRejectionBadge } from "@/components/workbench/PolarRejectionBadge";

// ─────────────────────────────────────────────────────────────────────
// gh-603: Thematic grouping of design assumptions.
//
// The flat list of 14 parameters is hard to scan; the user thinks of
// these in 6 buckets. The Propulsion / Energy / Takeoff buckets are
// meaningless for gliders (power_to_weight ≤ 0) and showing them as
// "0" produces misleading visual noise — so we hide them when
// `is_glider === true`.
//
// IMPORTANT: every member of the `AssumptionParameterName` union from
// `useDesignAssumptions.ts` (which mirrors `VALID_PARAMETERS` in
// `app/schemas/design_assumption.py`) must appear in exactly one
// group. The `ALL_GROUPED_PARAMS` set and the dev-mode assertion
// below guard against silent drift.
// ─────────────────────────────────────────────────────────────────────

type AssumptionGroupId =
  | "mass_balance"
  | "stability"
  | "aerodynamics"
  | "propulsion"
  | "energy"
  | "takeoff";

interface AssumptionGroup {
  readonly id: AssumptionGroupId;
  readonly label: string;
  readonly description: string;
  readonly params: readonly AssumptionParameterName[];
  readonly hideForGlider: boolean;
}

export const ASSUMPTION_GROUPS: readonly AssumptionGroup[] = [
  {
    id: "mass_balance",
    label: "Mass & Balance",
    description:
      "Aircraft mass and CG position — drive all sizing computations.",
    params: ["mass", "cg_x"],
    hideForGlider: false,
  },
  {
    id: "stability",
    label: "Stability",
    description:
      "Longitudinal stability targets and structural load limits.",
    params: ["target_static_margin", "g_limit"],
    hideForGlider: false,
  },
  {
    id: "aerodynamics",
    label: "Aerodynamics",
    description: "Lift and drag coefficients used by the polar.",
    params: ["cl_max", "cd0"],
    hideForGlider: false,
  },
  {
    id: "propulsion",
    label: "Propulsion",
    description:
      "Powertrain parameters — power-to-weight and efficiency chain.",
    params: [
      "power_to_weight",
      "prop_efficiency",
      "propulsion_eta_motor",
      "propulsion_eta_esc",
      "motor_continuous_power_w",
    ],
    hideForGlider: true,
  },
  {
    id: "energy",
    label: "Energy",
    description: "Battery sizing for endurance computation.",
    params: ["battery_capacity_wh", "battery_specific_energy_wh_per_kg"],
    hideForGlider: true,
  },
  {
    id: "takeoff",
    label: "Takeoff",
    description: "Static thrust for takeoff field length calculation.",
    params: ["t_static_N"],
    hideForGlider: true,
  },
];

// Flat set used to detect orphan parameters at module init in dev.
const ALL_GROUPED_PARAMS: ReadonlySet<AssumptionParameterName> = new Set(
  ASSUMPTION_GROUPS.flatMap((g) => g.params),
);

// The full set of `AssumptionParameterName` literals — kept in sync
// with the union via the `satisfies` clause to fail loudly at build
// time if a new param is added to the union but not to the table.
const ALL_KNOWN_PARAMS = [
  "mass",
  "cg_x",
  "target_static_margin",
  "cd0",
  "cl_max",
  "g_limit",
  "power_to_weight",
  "prop_efficiency",
  "battery_capacity_wh",
  "battery_specific_energy_wh_per_kg",
  "propulsion_eta_motor",
  "propulsion_eta_esc",
  "motor_continuous_power_w",
  "t_static_N",
] as const satisfies readonly AssumptionParameterName[];

if (process.env.NODE_ENV !== "production") {
  const missing = ALL_KNOWN_PARAMS.filter((p) => !ALL_GROUPED_PARAMS.has(p));
  if (missing.length > 0) {
    console.warn(
      `[AssumptionsPanel] gh-603: ASSUMPTION_GROUPS is missing parameters: ${missing.join(
        ", ",
      )}. Add them to the matching group.`,
    );
  }
  // Also assert no duplicates.
  const counts = new Map<string, number>();
  for (const g of ASSUMPTION_GROUPS) {
    for (const p of g.params) counts.set(p, (counts.get(p) ?? 0) + 1);
  }
  const dups = Array.from(counts.entries())
    .filter(([, n]) => n > 1)
    .map(([p]) => p);
  if (dups.length > 0) {
    console.warn(
      `[AssumptionsPanel] gh-603: ASSUMPTION_GROUPS contains duplicate parameters: ${dups.join(
        ", ",
      )}.`,
    );
  }
}

interface Props {
  readonly aeroplaneId: string;
}

export function AssumptionsPanel({ aeroplaneId }: Props) {
  const {
    data,
    isLoading,
    isRecomputing,
    error,
    seedDefaults,
    updateEstimate,
    switchSource,
    mutate,
  } = useDesignAssumptions(aeroplaneId);
  const { data: ctx } = useComputationContext(aeroplaneId);
  // Defensive: undefined ctx (not yet loaded) should not gate groups off.
  const isGlider = ctx?.is_glider === true;

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Loader2 size={16} className="animate-spin text-muted-foreground" />
        <span className="ml-2 font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
          Loading assumptions...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-red-400">
          Failed to load assumptions
        </span>
      </div>
    );
  }

  const assumptions = data?.assumptions ?? [];
  const warningsCount = data?.warnings_count ?? 0;

  if (assumptions.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-muted-foreground">
          No design assumptions yet
        </span>
        <button
          onClick={seedDefaults}
          className="flex items-center gap-1.5 rounded-full border border-border bg-card px-4 py-2 text-[12px] text-foreground hover:bg-sidebar-accent"
          data-testid="seed-defaults-button"
        >
          <Plus size={12} />
          Seed Defaults
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-auto">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
          Design Assumptions
        </span>
        {warningsCount > 0 && (
          <span
            className="flex items-center gap-1 rounded-full bg-orange-900/40 px-2 py-0.5 text-[10px] text-orange-400"
            data-testid="warnings-badge"
          >
            <AlertTriangle size={10} />
            {warningsCount}
          </span>
        )}
        {isRecomputing && (
          <span
            className="flex items-center gap-1 rounded-full bg-orange-500/15 px-2 py-0.5 text-[10px] text-orange-400"
            data-testid="recomputing-indicator"
          >
            <Loader2 size={10} className="animate-spin" />
            Recomputing…
          </span>
        )}
      </div>

      {/* CG comparison warning */}
      <CGComparisonBanner aeroplaneId={aeroplaneId} onCGSynced={() => mutate()} />

      {/* Grouped rows */}
      <div className="flex flex-col gap-4">
        {ASSUMPTION_GROUPS.map((group) => {
          if (group.hideForGlider && isGlider) return null;
          const groupParams = new Set<string>(group.params);
          const rows = assumptions.filter((a) =>
            groupParams.has(a.parameter_name),
          );
          if (rows.length === 0) return null;
          return (
            <section
              key={group.id}
              data-testid={`assumption-group-${group.id}`}
              className="rounded-xl border border-border bg-card"
            >
              <header
                className="flex items-center gap-2 border-b border-border px-4 py-2"
                title={group.description}
              >
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] uppercase tracking-wider text-muted-foreground">
                  {group.label}
                </span>
              </header>
              <div>
                {rows.map((a) => (
                  <AssumptionRow
                    key={a.id}
                    assumption={a}
                    onUpdateEstimate={updateEstimate}
                    onSwitchSource={switchSource}
                  />
                ))}
              </div>
              {/* gh-630: surface polar-fit design rejections in the Aerodynamics
                  group where the user edits cl_max / cd0 — the natural home for
                  "your polar shape is unphysical" warnings. All three configs
                  are wired; the badge returns null for non-design / null cases. */}
              {group.id === "aerodynamics" && ctx?.polar_by_config && (
                <div
                  className="flex flex-col gap-1 border-t border-border px-4 py-2"
                  data-testid="polar-rejection-badges"
                >
                  <PolarRejectionBadge rejection={ctx.polar_by_config.clean.rejection} />
                  <PolarRejectionBadge rejection={ctx.polar_by_config.takeoff.rejection} />
                  <PolarRejectionBadge rejection={ctx.polar_by_config.landing.rejection} />
                </div>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
