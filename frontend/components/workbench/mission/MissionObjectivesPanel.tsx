"use client";

import React, { useRef, useState } from "react";
import { useMissionObjectives, type MissionObjective } from "@/hooks/useMissionObjectives";
import { useMissionPresets } from "@/hooks/useMissionPresets";

interface Props {
  readonly aeroplaneId: string;
}

export function MissionObjectivesPanel({ aeroplaneId }: Props) {
  const { data: persisted, update } = useMissionObjectives(aeroplaneId);
  const { data: presets } = useMissionPresets();
  const [draft, setDraft] = useState<MissionObjective | null>(null);
  const [bannerKey, setBannerKey] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // "Adjust state when a prop changes" pattern — avoids useEffect+setState
  // (which react-hooks/set-state-in-effect forbids). Seed draft once on first
  // server response; subsequent SWR revalidations are intentionally ignored so
  // the user's in-flight edits are not clobbered.
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
  };

  const activePreset = presets.find((p) => p.id === draft.mission_type);

  return (
    <div className="flex h-full flex-col gap-3">
      <h3 className="text-sm font-semibold text-orange-500">⊙ Mission Objectives</h3>

      {bannerKey && activePreset && (
        <div className="rounded border-l-2 border-orange-500 bg-orange-500/10 p-3 text-xs">
          <div className="font-semibold text-orange-500">
            ⚡ Mission auf <span className="text-white">{activePreset.label}</span> gesetzt — Estimates angepasst
          </div>
          <div className="mt-1 font-mono text-[10px] text-foreground/80">
            {Object.entries(activePreset.suggested_estimates).map(([k, v]) => `${k}=${v}`).join(" · ")}
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
