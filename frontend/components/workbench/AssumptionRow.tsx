"use client";

import { useState, useRef } from "react";
import { ArrowLeftRight } from "lucide-react";
import type { Assumption } from "@/hooks/useDesignAssumptions";

const PARAM_LABELS: Record<string, string> = {
  mass: "Total Mass",
  cg_x: "CG Position (X)",
  target_static_margin: "Target Static Margin",
  cd0: "Zero-Lift Drag (CD₀)",
  cl_max: "Max Lift Coefficient (CL_max)",
  g_limit: "Load Factor Limit",
};

function divergenceColor(level: Assumption["divergence_level"]): string {
  if (level === "info") return "text-blue-400";
  if (level === "warning") return "text-orange-400";
  return "text-red-400";
}

function divergenceSuffix(level: Assumption["divergence_level"]): string {
  if (level === "warning") return " — review recommended";
  if (level === "alert") return " — significant!";
  return "";
}

function DivergenceIndicator({
  level,
  pct,
}: Readonly<{ level: Assumption["divergence_level"]; pct: number | null }>) {
  if (level === "none" || pct == null) return null;

  const colorClass = divergenceColor(level);
  const suffix = divergenceSuffix(level);

  return (
    <span className={`text-[11px] ${colorClass}`}>
      {pct.toFixed(1)}% divergence{suffix}
    </span>
  );
}

function SourceBadge({ assumption }: Readonly<{ assumption: Assumption }>) {
  if (assumption.is_design_choice) {
    return (
      <span className="rounded-full bg-zinc-700 px-2 py-0.5 text-[10px] text-zinc-300">
        design choice
      </span>
    );
  }
  if (assumption.active_source === "CALCULATED") {
    return (
      <span className="rounded-full bg-green-900/40 px-2 py-0.5 text-[10px] text-green-400">
        &#x2713; calculated
      </span>
    );
  }
  return (
    <span className="rounded-full bg-orange-900/40 px-2 py-0.5 text-[10px] text-orange-400">
      &#x26A0; estimate
    </span>
  );
}

interface Props {
  readonly assumption: Assumption;
  readonly onUpdateEstimate: (paramName: string, value: number) => void;
  readonly onSwitchSource: (
    paramName: string,
    source: "ESTIMATE" | "CALCULATED",
  ) => void;
}

export function AssumptionRow({
  assumption,
  onUpdateEstimate,
  onSwitchSource,
}: Props) {
  // Percentage units (e.g. "% MAC") store the value as a decimal fraction
  // (0.12) but the user thinks in 12%. Display × 100, parse ÷ 100.
  const isPercent = assumption.unit.includes("%");
  const toDisplay = (v: number) => (isPercent ? v * 100 : v);
  const fromDisplay = (v: number) => (isPercent ? v / 100 : v);
  const displayUnit = isPercent ? "%" : assumption.unit;
  const formatNumber = (v: number) =>
    isPercent ? toDisplay(v).toFixed(1) : v.toPrecision(4);

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(toDisplay(assumption.estimate_value)));
  const inputRef = useRef<HTMLInputElement>(null);

  const label =
    PARAM_LABELS[assumption.parameter_name] ?? assumption.parameter_name;

  function commitEdit() {
    const parsedDisplay = parseFloat(draft);
    if (Number.isFinite(parsedDisplay)) {
      const parsed = fromDisplay(parsedDisplay);
      if (parsed !== assumption.estimate_value) {
        onUpdateEstimate(assumption.parameter_name, parsed);
      }
    }
    setEditing(false);
  }

  function startEdit() {
    setDraft(String(toDisplay(assumption.estimate_value)));
    setEditing(true);
    // Focus after render
    setTimeout(() => inputRef.current?.select(), 0);
  }

  const canToggleSource =
    !assumption.is_design_choice && assumption.calculated_value != null;

  const toggleSource = () => {
    const next =
      assumption.active_source === "ESTIMATE" ? "CALCULATED" : "ESTIMATE";
    onSwitchSource(assumption.parameter_name, next);
  };

  return (
    <div className="flex items-center gap-3 border-b border-border px-4 py-2.5 last:border-b-0">
      {/* Label */}
      <span className="min-w-[180px] text-[12px] text-foreground">
        {label}
      </span>

      {/* Effective value */}
      <span className="min-w-[90px] font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground">
        {formatNumber(assumption.effective_value)}{" "}
        <span className="text-muted-foreground">{displayUnit}</span>
      </span>

      {/* Source badge */}
      <SourceBadge assumption={assumption} />

      {/* Estimate editor */}
      <div className="flex min-w-[120px] items-center gap-1">
        {!assumption.is_design_choice && (
          <span className="text-[10px] text-muted-foreground">est:</span>
        )}
        {editing ? (
          <input
            ref={inputRef}
            type="number"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commitEdit}
            onKeyDown={(e) => {
              if (e.key === "Enter") commitEdit();
              if (e.key === "Escape") setEditing(false);
            }}
            className="w-[80px] rounded border border-border bg-card px-1.5 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground outline-none focus:border-orange-400"
            data-testid={`estimate-input-${assumption.parameter_name}`}
          />
        ) : (
          <button
            onClick={startEdit}
            className="rounded px-1.5 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
            data-testid={`estimate-display-${assumption.parameter_name}`}
          >
            {formatNumber(assumption.estimate_value)}
          </button>
        )}
      </div>

      {/* Source toggle */}
      {canToggleSource && (
        <button
          onClick={toggleSource}
          className="flex items-center gap-1 rounded-full border border-border px-2 py-1 text-[10px] text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
          title={`Switch to ${assumption.active_source === "ESTIMATE" ? "calculated" : "estimate"}`}
          data-testid={`toggle-source-${assumption.parameter_name}`}
        >
          <ArrowLeftRight size={10} />
          {assumption.active_source === "ESTIMATE" ? "Use calc" : "Use est"}
        </button>
      )}

      {/* Spacer */}
      <span className="flex-1" />

      {/* Divergence */}
      <DivergenceIndicator
        level={assumption.divergence_level}
        pct={assumption.divergence_pct}
      />
    </div>
  );
}
