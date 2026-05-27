"use client";

import React, { useRef, useState } from "react";
import { useMissionObjectives, type MissionObjective } from "@/hooks/useMissionObjectives";
import { useMissionPresets, type MissionPreset, type AxisName } from "@/hooks/useMissionPresets";
import { normalizedToRaw } from "@/lib/missionScale";
import { InfoLabel } from "@/components/workbench/InfoLabel";

interface Props {
  readonly aeroplaneId: string;
}

/**
 * Per-field info-tooltip copy for the Mission Tab inputs (gh-610).
 * Tooltips surface on hover OR keyboard focus to keep the panel
 * discoverable without overwhelming users who already know the fields.
 */
const FIELD_DESCRIPTIONS = {
  mission_type:
    "Preset that suggests defaults for the editable performance targets and the design assumptions. Changing the preset applies its suggested values via the banner Apply button.",
  target_cruise_mps:
    "Design cruise speed at altitude. Drives propeller selection, drag analysis, and the cruise-constraint curve on the matching chart.",
  target_stall_safety:
    "Safety factor on stall speed (×); e.g. 1.8 means landing approach at 1.8 × V_stall. Lower = closer to stall = more demanding pilot skill.",
  target_maneuver_n:
    "Limit load factor n_max (g). Sets structural g-loading; CS-22 utility category = 5.3, aerobatic = 6+.",
  target_glide_ld:
    "Minimum lift-to-drag ratio in the cruise polar. Sailplanes ≥ 20; sport ≥ 10; trainer ≥ 8.",
  target_climb_energy:
    "Energy-per-time proxy for climb performance: rate-of-climb × g-load. Higher = stronger powerplant relative to weight.",
  target_wing_loading_n_m2:
    "Design wing loading W/S (N/m²). Sets stall speed and the W/S-axis position on the matching chart. Higher = smaller wing but higher stall speed.",
  available_runway_m:
    "Hard ground length available for take-off / landing (m). Sets the take-off and landing constraint curves on the matching chart.",
  runway_type:
    "Surface affecting rolling friction (grass higher, asphalt lower) and crash-landing tolerance (belly = no gear).",
  t_static_N:
    "Powertrain static thrust at zero airspeed (N). Sets the T/W ratio on the matching chart. For gliders, 0.",
  takeoff_mode:
    "runway = wheeled take-off; hand_launch = thrown by hand (RC); bungee = elastic catapult (gliders); catapult = launched device.",
  // gh-477: landing-field-length inputs. The three feed
  // ``computation_context.landing_field_length_m`` + the L_landing chip.
  landing_surface:
    "Expected landing surface. Drives μ_eff: short grass μ=0.15, long grass μ=0.22, hard paved (no brake) μ=0.07, soft soil μ=0.30, belly on grass μ=0.40, net/cable recovery → no ground roll.",
  landing_safety_factor:
    "Safety multiplier applied to the computed landing length (s_flare + s_ground). Typical 1.5–2.0. Higher = more conservative field-length recommendation.",
  available_field_length_m:
    "Length of the planned landing field (m). When set, the L_landing chip turns green (sufficient) or red (insufficient). Leave at 0 to suppress the comparison and show only the required length.",
} as const;

// gh-477: landing-surface options for the dropdown. Plain-English
// labels for the user, kebab-case values for the backend literal.
const LANDING_SURFACE_OPTIONS: { value: string; label: string }[] = [
  { value: "grass_short", label: "Short grass" },
  { value: "grass_long", label: "Long grass" },
  { value: "hard_paved", label: "Hard paved (no brake)" },
  { value: "soft_soil", label: "Soft soil" },
  { value: "belly_grass", label: "Belly landing on grass" },
  { value: "net_recovery", label: "Net / cable recovery" },
];

/** Per-axis → MissionObjective target-field mapping (gh-601). */
const AXIS_TO_TARGET_FIELD: Partial<Record<AxisName, keyof MissionObjective>> = {
  stall_safety: "target_stall_safety",
  glide: "target_glide_ld",
  climb: "target_climb_energy",
  cruise: "target_cruise_mps",
  maneuver: "target_maneuver_n",
  wing_loading: "target_wing_loading_n_m2",
  // field_friendliness — no direct target field (out of scope per #601).
};

const TARGET_FIELD_LABELS: Record<string, string> = {
  target_stall_safety: "Stall Safety",
  target_glide_ld: "Glide (L/D)",
  target_climb_energy: "Climb Energy",
  target_cruise_mps: "Cruise (m/s)",
  target_maneuver_n: "Maneuver (g)",
  target_wing_loading_n_m2: "Wing Loading (N/m²)",
};

/** Suggested target value computed from a preset's polygon × axis ranges. */
interface SuggestedTarget {
  readonly axis: AxisName;
  readonly field: keyof MissionObjective;
  readonly label: string;
  readonly current: number;
  readonly suggested: number;
}

function computeSuggestedTargets(
  preset: MissionPreset,
  draft: MissionObjective,
): SuggestedTarget[] {
  const out: SuggestedTarget[] = [];
  for (const [axis, field] of Object.entries(AXIS_TO_TARGET_FIELD) as [
    AxisName,
    keyof MissionObjective,
  ][]) {
    const score = preset.target_polygon[axis];
    const range = preset.axis_ranges[axis];
    if (score === undefined || range === undefined) continue;
    const suggested = normalizedToRaw(score, range);
    const current = draft[field] as number;
    out.push({
      axis,
      field,
      label: TARGET_FIELD_LABELS[field] ?? field,
      current,
      suggested,
    });
  }
  return out;
}

/** Row is shown only when the relative delta exceeds 0.5%. */
function isMeaningfulDiff(current: number, suggested: number): boolean {
  const denom = Math.max(Math.abs(current), Math.abs(suggested), 1e-9);
  return Math.abs(current - suggested) / denom > 0.005;
}

const fmt = (n: number): string =>
  Number.isInteger(n) ? n.toFixed(1) : n.toFixed(2);

export function MissionObjectivesPanel({ aeroplaneId }: Props) {
  const { data: persisted, update } = useMissionObjectives(aeroplaneId);
  const { data: presets } = useMissionPresets();
  const [draft, setDraft] = useState<MissionObjective | null>(null);
  const [bannerKey, setBannerKey] = useState<string | null>(null);
  const [bannerVisible, setBannerVisible] = useState<boolean>(false);
  const [lastAeroplaneId, setLastAeroplaneId] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // "Adjust state when a prop changes" pattern — avoids useEffect+setState
  // (which react-hooks/set-state-in-effect forbids). When the aeroplaneId
  // changes (user switched aeroplane), drop the previous draft so the next
  // server response for the new aeroplane re-seeds it — otherwise the panel
  // would render aeroplane A's data while writes target aeroplane B's URL
  // (gh-602, data-corruption risk). For the SAME aeroplane, the draft is
  // seeded once on the first server response; subsequent SWR revalidations
  // are intentionally ignored so the user's in-flight edits are not clobbered.
  if (lastAeroplaneId !== aeroplaneId) {
    setLastAeroplaneId(aeroplaneId);
    setDraft(null);
  }
  if (persisted && !draft) setDraft({ ...persisted });

  if (!draft || !presets) return <div className="text-muted-foreground text-sm">Loading…</div>;

  const set = <K extends keyof MissionObjective>(key: K, value: MissionObjective[K]) => {
    setDraft((d) => (d ? { ...d, [key]: value } : d));
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      void update({ ...(draft as MissionObjective), [key]: value });
    }, 300);
  };

  const onMissionTypeChange = (id: string) => {
    set("mission_type", id);
    setBannerKey(id);
    setBannerVisible(true);
  };

  const activePreset = presets.find((p) => p.id === draft.mission_type);

  const suggestedTargets =
    activePreset && bannerKey ? computeSuggestedTargets(activePreset, draft) : [];
  const diffRows = suggestedTargets.filter((r) => isMeaningfulDiff(r.current, r.suggested));

  const handleApply = () => {
    if (!activePreset) return;
    // Snapshot the current draft and apply all suggested targets at once.
    // We cancel any pending debounced update synchronously here so the older
    // (mission_type-only) PUT cannot race past this one.
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    const next = { ...draft };
    for (const row of suggestedTargets) {
      (next as unknown as Record<string, number>)[row.field as string] = row.suggested;
    }
    setDraft(next);
    void update(next);
    setBannerVisible(false);
  };

  const handleDismiss = () => {
    setBannerVisible(false);
  };

  const showBanner = bannerVisible && bannerKey && activePreset;

  return (
    <div className="flex h-full flex-col gap-3">
      <h3 className="text-sm font-semibold text-orange-500">⊙ Mission Objectives</h3>

      {showBanner && (
        <div
          className="rounded border-l-2 border-orange-500 bg-orange-500/10 p-3 text-xs"
          data-testid="mission-apply-banner"
        >
          <div className="font-semibold text-orange-500">
            ⚡ Mission set to <span className="text-white">{activePreset.label}</span> — estimates applied
          </div>
          <div className="mt-1 font-mono text-[10px] text-foreground/80">
            {Object.entries(activePreset.suggested_estimates)
              .map(([k, v]) => `${k}=${v}`)
              .join(" · ")}
          </div>

          {diffRows.length > 0 && (
            <div className="mt-2">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
                Suggested Performance Targets
              </div>
              <table className="w-full font-mono text-[10px]">
                <tbody>
                  {diffRows.map((row) => (
                    <tr key={row.field} data-testid={`diff-row-${row.field}`}>
                      <td className="py-0.5 pr-2 text-foreground/80">{row.label}</td>
                      <td className="py-0.5 pr-2 text-right text-muted-foreground tabular-nums">
                        {fmt(row.current)}
                      </td>
                      <td className="py-0.5 pr-1 text-muted-foreground">→</td>
                      <td className="py-0.5 text-right text-orange-300 tabular-nums">
                        {fmt(row.suggested)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="mt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={handleDismiss}
              className="rounded border border-border bg-transparent px-3 py-1 text-[11px] text-muted-foreground hover:bg-card hover:text-foreground"
            >
              Dismiss
            </button>
            <button
              type="button"
              onClick={handleApply}
              disabled={diffRows.length === 0}
              className="rounded bg-orange-500 px-3 py-1 text-[11px] font-semibold text-black hover:bg-orange-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Apply
            </button>
          </div>
        </div>
      )}

      <div className="space-y-2">
        <InfoLabel
          label="Mission Type"
          description={FIELD_DESCRIPTIONS.mission_type}
          htmlFor="mission-type"
        />
        <select
          id="mission-type" aria-label="Mission Type"
          className="w-full rounded bg-background border border-border px-2 py-1.5 text-sm"
          value={draft.mission_type}
          onChange={(e) => onMissionTypeChange(e.target.value)}
        >
          {presets.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
        </select>
      </div>

      <div className="text-[10px] uppercase tracking-wider text-muted-foreground border-b border-border pb-1">
        Performance Targets
      </div>
      <div className="grid grid-cols-2 gap-2">
        <NumField label="Target Cruise" suffix="m/s" value={draft.target_cruise_mps} onChange={(v) => set("target_cruise_mps", v)} description={FIELD_DESCRIPTIONS.target_cruise_mps}/>
        <NumField label="Stall Safety" suffix="–" value={draft.target_stall_safety} onChange={(v) => set("target_stall_safety", v)} description={FIELD_DESCRIPTIONS.target_stall_safety}/>
        <NumField label="Max Maneuver" suffix="g" value={draft.target_maneuver_n} onChange={(v) => set("target_maneuver_n", v)} description={FIELD_DESCRIPTIONS.target_maneuver_n}/>
        <NumField label="Min Glide (L/D)" suffix="–" value={draft.target_glide_ld} onChange={(v) => set("target_glide_ld", v)} description={FIELD_DESCRIPTIONS.target_glide_ld}/>
        <NumField label="Climb Energy" suffix="–" value={draft.target_climb_energy} onChange={(v) => set("target_climb_energy", v)} description={FIELD_DESCRIPTIONS.target_climb_energy}/>
        <NumField label="Target Wing Load" suffix="N/m²" value={draft.target_wing_loading_n_m2} onChange={(v) => set("target_wing_loading_n_m2", v)} description={FIELD_DESCRIPTIONS.target_wing_loading_n_m2}/>
      </div>

      <div className="text-[10px] uppercase tracking-wider text-muted-foreground border-b border-border pb-1 mt-2">
        Field Performance
      </div>
      <div className="grid grid-cols-2 gap-2">
        <NumField label="Available Runway" suffix="m" value={draft.available_runway_m} onChange={(v) => set("available_runway_m", v)} description={FIELD_DESCRIPTIONS.available_runway_m}/>
        <SelectField label="Runway Type" value={draft.runway_type} options={["grass", "asphalt", "belly"]} onChange={(v) => set("runway_type", v as MissionObjective["runway_type"])} description={FIELD_DESCRIPTIONS.runway_type}/>
        <NumField label="Static Thrust" suffix="N" value={draft.t_static_N} onChange={(v) => set("t_static_N", v)} description={FIELD_DESCRIPTIONS.t_static_N}/>
        <SelectField label="Takeoff Mode" value={draft.takeoff_mode} options={["runway", "hand_launch", "bungee", "catapult"]} onChange={(v) => set("takeoff_mode", v as MissionObjective["takeoff_mode"])} description={FIELD_DESCRIPTIONS.takeoff_mode}/>
      </div>

      <div className="text-[10px] uppercase tracking-wider text-muted-foreground border-b border-border pb-1 mt-2">
        Landing Field (L_landing chip)
      </div>
      <div className="grid grid-cols-2 gap-2">
        <LabelledSelectField
          label="Landing Surface"
          value={draft.landing_surface ?? "grass_short"}
          options={LANDING_SURFACE_OPTIONS}
          onChange={(v) => set("landing_surface", v as MissionObjective["landing_surface"])}
          description={FIELD_DESCRIPTIONS.landing_surface}
        />
        <NumField
          label="Landing Safety Factor"
          suffix="×"
          value={draft.landing_safety_factor ?? 1.5}
          onChange={(v) => set("landing_safety_factor", v)}
          description={FIELD_DESCRIPTIONS.landing_safety_factor}
        />
        <NumField
          label="Available Landing Field"
          suffix="m"
          value={draft.available_field_length_m ?? 0}
          onChange={(v) =>
            // 0 → null so the backend skips the green/red comparison and the
            // chip renders only the required length (issue: "available unset
            // → don't render the comparison").
            set("available_field_length_m", (v > 0 ? v : null) as unknown as number)
          }
          description={FIELD_DESCRIPTIONS.available_field_length_m}
        />
      </div>
    </div>
  );
}

// gh-477: variant of SelectField that takes labelled options (the
// landing-surface dropdown's value is a kebab-case literal but the
// user reads a plain-English label).
function LabelledSelectField(props: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
  description?: string;
}) {
  const id = `f-${props.label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <div>
      <InfoLabel label={props.label} description={props.description} htmlFor={id} />
      <select
        id={id}
        aria-label={props.label}
        className="w-full rounded bg-background border border-border px-2 py-1.5 text-sm"
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
      >
        {props.options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function NumField(props: { label: string; suffix: string; value: number; onChange: (v: number) => void; description?: string }) {
  const id = `f-${props.label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <div>
      <InfoLabel label={props.label} description={props.description} htmlFor={id} />
      <div className="flex">
        <input
          id={id} aria-label={props.label} type="number"
          className="flex-1 rounded-l bg-background border border-border px-2 py-1.5 text-sm font-mono"
          value={props.value}
          onChange={(e) => props.onChange(parseFloat(e.target.value))}
        />
        <span className="rounded-r bg-card border border-l-0 border-border px-2 py-1.5 text-[10px] text-muted-foreground">
          {props.suffix}
        </span>
      </div>
    </div>
  );
}

function SelectField(props: { label: string; value: string; options: string[]; onChange: (v: string) => void; description?: string }) {
  const id = `f-${props.label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <div>
      <InfoLabel label={props.label} description={props.description} htmlFor={id} />
      <select id={id} aria-label={props.label}
        className="w-full rounded bg-background border border-border px-2 py-1.5 text-sm"
        value={props.value} onChange={(e) => props.onChange(e.target.value)}>
        {props.options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  );
}
