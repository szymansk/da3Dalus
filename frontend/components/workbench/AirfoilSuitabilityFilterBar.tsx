"use client";

/**
 * Airfoil suitability filter bar (gh-835).
 *
 * Renders:
 *  - Family chips (multi-select, OR logic)
 *  - Role-tag chips: winglet / h_stab / v_stab / acro / low_re (multi-select, OR logic)
 *  - Thickness min–max number inputs
 *
 * All filters are additive (AND across dimensions, OR within each dimension).
 * Empty selection in a dimension = "no filter for that dimension".
 *
 * The component is STATELESS — callers own the filter state.
 */

import type { AirfoilFamily, RoleTag } from "@/hooks/useAirfoilSuitability";
import { FilterChipGroup } from "./FilterChipGroup";

// ── Option definitions (displayed labels) ────────────────────────────────────

const FAMILY_OPTIONS: { value: AirfoilFamily; label: string; description: string }[] = [
  { value: "flat_bottom",    label: "Flat",      description: "Flat-bottom — classic trainer/slow-flier" },
  { value: "semi_symmetric", label: "Semi-sym",  description: "Semi-symmetric — sport/aerobatic" },
  { value: "symmetric",      label: "Symmetric", description: "Symmetric — acro, stabiliser" },
  { value: "cambered",       label: "Cambered",  description: "Cambered — sailplane, efficient at cruise CL" },
  { value: "reflexed",       label: "Reflexed",  description: "Reflexed — flying wing / Nuri (self-trimming)" },
];

const TAG_OPTIONS: { value: RoleTag; label: string; description: string }[] = [
  { value: "winglet",      label: "Winglet",  description: "Thin, clean — suitable for winglets" },
  { value: "h_stabilizer", label: "H-Stab",   description: "Symmetric, t 6–15 % — horizontal stabiliser" },
  { value: "v_stabilizer", label: "V-Stab",   description: "Symmetric, t 6–15 % — vertical stabiliser" },
  { value: "acro",         label: "Acro",     description: "Symmetric, t 7–12 % — aerobatic cross-section" },
  { value: "low_re",       label: "Low Re",   description: "Good behaviour at Re ≤ 150 000" },
  { value: "high_re",      label: "High Re",  description: "Good behaviour at Re ≥ 500 000 (approximate — grid tops at 750k)" },
];

// ── Props ─────────────────────────────────────────────────────────────────────

export interface AirfoilSuitabilityFilters {
  families: AirfoilFamily[];
  tags: RoleTag[];
  thicknessMinPct: string;
  thicknessMaxPct: string;
}

export function emptyFilters(): AirfoilSuitabilityFilters {
  return { families: [], tags: [], thicknessMinPct: "", thicknessMaxPct: "" };
}

/**
 * Returns true when all filter dimensions are empty / "no filter applied".
 */
export function isFiltersEmpty(f: AirfoilSuitabilityFilters): boolean {
  return (
    f.families.length === 0 &&
    f.tags.length === 0 &&
    f.thicknessMinPct === "" &&
    f.thicknessMaxPct === ""
  );
}

interface AirfoilSuitabilityFilterBarProps {
  filters: AirfoilSuitabilityFilters;
  onFiltersChange: (next: AirfoilSuitabilityFilters) => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function AirfoilSuitabilityFilterBar({
  filters,
  onFiltersChange,
}: Readonly<AirfoilSuitabilityFilterBarProps>) {
  const { families, tags, thicknessMinPct, thicknessMaxPct } = filters;

  function setFamilies(next: AirfoilFamily[]) {
    onFiltersChange({ ...filters, families: next });
  }
  function setTags(next: RoleTag[]) {
    onFiltersChange({ ...filters, tags: next });
  }
  function setThicknessMin(v: string) {
    onFiltersChange({ ...filters, thicknessMinPct: v });
  }
  function setThicknessMax(v: string) {
    onFiltersChange({ ...filters, thicknessMaxPct: v });
  }

  const hasAnyFilter = !isFiltersEmpty(filters);

  return (
    <div
      data-testid="suitability-filter-bar"
      className="flex flex-col gap-2 rounded-xl border border-border bg-card-muted px-3 py-2.5"
    >
      {/* Header row */}
      <div className="flex items-center gap-2">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          Filter
        </span>
        {hasAnyFilter && (
          <button
            type="button"
            data-testid="filter-clear-btn"
            onClick={() => onFiltersChange(emptyFilters())}
            className="ml-auto rounded-full border border-border px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground hover:border-primary/50 hover:text-primary"
          >
            Zurücksetzen
          </button>
        )}
      </div>

      {/* Family chips */}
      <FilterChipGroup
        options={FAMILY_OPTIONS}
        selected={families}
        onChange={setFamilies}
        ariaLabel="Familie filtern"
      />

      {/* Role-tag chips */}
      <FilterChipGroup
        options={TAG_OPTIONS}
        selected={tags}
        onChange={setTags}
        ariaLabel="Einsatzrolle filtern"
      />

      {/* Thickness range */}
      <div className="flex items-center gap-2">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
          t/c
        </span>
        <input
          type="number"
          aria-label="Minimale Dicke (%)"
          data-testid="thickness-min-input"
          value={thicknessMinPct}
          onChange={(e) => setThicknessMin(e.target.value)}
          placeholder="min"
          min={0}
          step={0.5}
          className="w-14 rounded-lg border border-border bg-input px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-foreground outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
        />
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
          –
        </span>
        <input
          type="number"
          aria-label="Maximale Dicke (%)"
          data-testid="thickness-max-input"
          value={thicknessMaxPct}
          onChange={(e) => setThicknessMax(e.target.value)}
          placeholder="max"
          min={0}
          step={0.5}
          className="w-14 rounded-lg border border-border bg-input px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-foreground outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
        />
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
          %
        </span>
      </div>
    </div>
  );
}
