"use client";

import useSWR from "swr";
import { useCallback } from "react";
import { API_BASE, fetcher } from "@/lib/fetcher";

// ---------------------------------------------------------------------------
// Types (matching backend schemas)
// ---------------------------------------------------------------------------

export interface ComponentToggle {
  component_uuid: string;
  enabled: boolean;
}

export interface MassOverride {
  component_uuid: string;
  mass_kg_override: number;
}

export interface PositionOverride {
  component_uuid: string;
  x_m_override: number;
  y_m_override?: number | null;
  z_m_override?: number | null;
}

export type AdhocCategory =
  | "pilot"
  | "payload"
  | "ballast"
  | "fuel"
  | "fpv_gear"
  | "other";

export interface AdhocItem {
  name: string;
  mass_kg: number;
  x_m: number;
  y_m: number;
  z_m: number;
  category: AdhocCategory;
}

export interface ComponentOverrides {
  toggles: ComponentToggle[];
  mass_overrides: MassOverride[];
  position_overrides: PositionOverride[];
  adhoc_items: AdhocItem[];
}

export type AircraftClass =
  | "rc_trainer"
  | "rc_aerobatic"
  | "rc_combust"
  | "uav_survey"
  | "glider"
  | "boxwing";

export interface LoadingScenario {
  id: number;
  aeroplane_id: number;
  name: string;
  aircraft_class: AircraftClass;
  component_overrides: ComponentOverrides;
  is_default: boolean;
}

export interface LoadingScenarioCreate {
  name: string;
  aircraft_class: AircraftClass;
  component_overrides: ComponentOverrides;
  is_default: boolean;
}

export interface LoadingScenarioUpdate {
  name?: string;
  aircraft_class?: AircraftClass;
  component_overrides?: ComponentOverrides;
  is_default?: boolean;
}

export type CgClassification = "error" | "warn" | "ok";

export interface CgEnvelope {
  cg_loading_fwd_m: number;
  cg_loading_aft_m: number;
  cg_stability_fwd_m: number;
  cg_stability_aft_m: number;
  sm_at_fwd: number;
  sm_at_aft: number;
  classification: CgClassification;
  warnings: string[];
}

export interface LoadingScenarioTemplate {
  name: string;
  component_overrides: ComponentOverrides;
  is_default: boolean;
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useLoadingScenarios(aeroplaneId: string | null) {
  const path = aeroplaneId
    ? `/aeroplanes/${aeroplaneId}/loading-scenarios`
    : null;

  const { data, error, isLoading, mutate } = useSWR<LoadingScenario[]>(
    path,
    fetcher,
  );

  const createScenario = useCallback(
    async (payload: LoadingScenarioCreate): Promise<LoadingScenario> => {
      if (!aeroplaneId) throw new Error("No aeroplaneId");
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/loading-scenarios`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`Failed to create scenario: ${res.status} ${body}`);
      }
      const created = (await res.json()) as LoadingScenario;
      await mutate();
      return created;
    },
    [aeroplaneId, mutate],
  );

  const updateScenario = useCallback(
    async (
      scenarioId: number,
      payload: LoadingScenarioUpdate,
    ): Promise<LoadingScenario> => {
      if (!aeroplaneId) throw new Error("No aeroplaneId");
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/loading-scenarios/${scenarioId}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`Failed to update scenario: ${res.status} ${body}`);
      }
      const updated = (await res.json()) as LoadingScenario;
      await mutate();
      return updated;
    },
    [aeroplaneId, mutate],
  );

  const deleteScenario = useCallback(
    async (scenarioId: number): Promise<void> => {
      if (!aeroplaneId) throw new Error("No aeroplaneId");
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/loading-scenarios/${scenarioId}`,
        { method: "DELETE" },
      );
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`Failed to delete scenario: ${res.status} ${body}`);
      }
      await mutate();
    },
    [aeroplaneId, mutate],
  );

  return {
    scenarios: data ?? [],
    isLoading,
    error: error ?? null,
    mutate,
    createScenario,
    updateScenario,
    deleteScenario,
  };
}

export function useCgEnvelope(aeroplaneId: string | null) {
  const path = aeroplaneId
    ? `/aeroplanes/${aeroplaneId}/cg-envelope`
    : null;

  const { data, error, isLoading, mutate } = useSWR<CgEnvelope>(
    path,
    fetcher,
  );

  return {
    envelope: data ?? null,
    isLoading,
    error: error ?? null,
    mutate,
  };
}

export function useLoadingScenarioTemplates(
  aeroplaneId: string | null,
  aircraftClass: AircraftClass,
) {
  const path = aeroplaneId
    ? `/aeroplanes/${aeroplaneId}/loading-scenarios/templates?aircraft_class=${aircraftClass}`
    : null;

  const { data, error, isLoading } = useSWR<LoadingScenarioTemplate[]>(
    path,
    fetcher,
  );

  return {
    templates: data ?? [],
    isLoading,
    error: error ?? null,
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export function emptyOverrides(): ComponentOverrides {
  return {
    toggles: [],
    mass_overrides: [],
    position_overrides: [],
    adhoc_items: [],
  };
}

export const AIRCRAFT_CLASS_LABELS: Record<AircraftClass, string> = {
  rc_trainer: "RC Trainer",
  rc_aerobatic: "RC Aerobatic",
  rc_combust: "RC Combust",
  uav_survey: "UAV Survey",
  glider: "Glider",
  boxwing: "Box Wing",
};
