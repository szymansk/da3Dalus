"use client";

import React, { useRef, useState } from "react";
import { useMissionObjectives, type MissionObjective } from "@/hooks/useMissionObjectives";
import { useMissionPresets, type MissionPreset, type AxisName } from "@/hooks/useMissionPresets";
import { normalizedToRaw } from "@/lib/missionScale";

interface Props {
  readonly aeroplaneId: string;
}

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
      (next as Record<string, number>)[row.field as string] = row.suggested;
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
        <label htmlFor="mission-type" className="block text-xs text-muted-foreground">
          Mission Type
        </label>
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
        <NumField label="Target Cruise" suffix="m/s" value={draft.target_cruise_mps} onChange={(v) => set("target_cruise_mps", v)}/>
        <NumField label="Stall Safety" suffix="–" value={draft.target_stall_safety} onChange={(v) => set("target_stall_safety", v)}/>
        <NumField label="Max Maneuver" suffix="g" value={draft.target_maneuver_n} onChange={(v) => set("target_maneuver_n", v)}/>
        <NumField label="Min Glide (L/D)" suffix="–" value={draft.target_glide_ld} onChange={(v) => set("target_glide_ld", v)}/>
        <NumField label="Climb Energy" suffix="–" value={draft.target_climb_energy} onChange={(v) => set("target_climb_energy", v)}/>
        <NumField label="Target Wing Load" suffix="N/m²" value={draft.target_wing_loading_n_m2} onChange={(v) => set("target_wing_loading_n_m2", v)}/>
      </div>

      <div className="text-[10px] uppercase tracking-wider text-muted-foreground border-b border-border pb-1 mt-2">
        Field Performance
      </div>
      <div className="grid grid-cols-2 gap-2">
        <NumField label="Available Runway" suffix="m" value={draft.available_runway_m} onChange={(v) => set("available_runway_m", v)}/>
        <SelectField label="Runway Type" value={draft.runway_type} options={["grass", "asphalt", "belly"]} onChange={(v) => set("runway_type", v as MissionObjective["runway_type"])}/>
        <NumField label="Static Thrust" suffix="N" value={draft.t_static_N} onChange={(v) => set("t_static_N", v)}/>
        <SelectField label="Takeoff Mode" value={draft.takeoff_mode} options={["runway", "hand_launch", "bungee", "catapult"]} onChange={(v) => set("takeoff_mode", v as MissionObjective["takeoff_mode"])}/>
      </div>
    </div>
  );
}

function NumField(props: { label: string; suffix: string; value: number; onChange: (v: number) => void }) {
  const id = `f-${props.label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <div>
      <label htmlFor={id} className="block text-xs text-muted-foreground mb-1">{props.label}</label>
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

function SelectField(props: { label: string; value: string; options: string[]; onChange: (v: string) => void }) {
  const id = `f-${props.label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <div>
      <label htmlFor={id} className="block text-xs text-muted-foreground mb-1">{props.label}</label>
      <select id={id} aria-label={props.label}
        className="w-full rounded bg-background border border-border px-2 py-1.5 text-sm"
        value={props.value} onChange={(e) => props.onChange(e.target.value)}>
        {props.options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  );
}
