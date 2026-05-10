"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import { X, ChevronUp, ChevronDown, Loader2, Info, Trash2 } from "lucide-react";
import type {
  StoredOperatingPoint,
  OperatingPointStatus,
  AVLTrimResult,
  AeroBuildupTrimResult,
  TrimConstraint,
  ControlSurface,
} from "@/hooks/useOperatingPoints";
import {
  AnalysisGoalCard,
  ControlAuthorityChart,
  DesignWarningBadges,
  MixerValuesCard,
  OpComparisonTable,
} from "./trim-interpretation";

const RAD_TO_DEG = 180 / Math.PI;

const STATUS_STYLES: Record<
  OperatingPointStatus,
  { bg: string; text: string; label: string; spinner?: boolean }
> = {
  TRIMMED: {
    bg: "bg-emerald-500/15",
    text: "text-emerald-400",
    label: "Trimmed",
  },
  NOT_TRIMMED: {
    bg: "bg-yellow-500/15",
    text: "text-yellow-400",
    label: "Not Trimmed",
  },
  LIMIT_REACHED: {
    bg: "bg-red-500/15",
    text: "text-red-400",
    label: "Limit Reached",
  },
  DIRTY: {
    bg: "bg-orange-500/15",
    text: "text-orange-400",
    label: "Outdated",
  },
  COMPUTING: {
    bg: "bg-orange-500/15",
    text: "text-orange-400",
    label: "Computing",
    spinner: true,
  },
};

type SortKey = "name" | "velocity" | "alpha" | "beta" | "config" | "status";
type SortDir = "asc" | "desc";

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "name", label: "Name" },
  { key: "velocity", label: "Velocity (m/s)" },
  { key: "alpha", label: "Alpha (deg)" },
  { key: "beta", label: "Beta (deg)" },
  { key: "config", label: "Config" },
  { key: "status", label: "Status" },
];

interface Props {
  readonly points: StoredOperatingPoint[];
  readonly isLoading: boolean;
  readonly isGenerating: boolean;
  readonly isTrimming: boolean;
  readonly error: string | null;
  readonly onGenerate: () => void;
  readonly onTrimWithAvl: (
    point: StoredOperatingPoint,
    constraints: TrimConstraint[],
  ) => Promise<AVLTrimResult | null>;
  readonly onTrimWithAerobuildup: (
    point: StoredOperatingPoint,
    trimVariable: string,
    targetCoefficient: string,
    targetValue: number,
  ) => Promise<AeroBuildupTrimResult | null>;
  readonly controlSurfaces: ControlSurface[];
  readonly onUpdateDeflections: (
    opId: number,
    deflections: Record<string, number> | null,
  ) => Promise<void>;
  readonly onDeleteOp?: (opId: number) => Promise<void>;
  readonly onDeleteAll?: () => Promise<void>;
  readonly onCreateOp?: (payload: {
    name: string;
    velocity: number;
    alpha: number;
    beta?: number;
    altitude?: number;
    config?: string;
  }) => Promise<void>;
}

function sortPoints(
  pts: StoredOperatingPoint[],
  key: SortKey,
  dir: SortDir,
): StoredOperatingPoint[] {
  const sorted = [...pts].sort((a, b) => {
    let cmp = 0;
    switch (key) {
      case "name":
        cmp = a.name.localeCompare(b.name);
        break;
      case "velocity":
        cmp = a.velocity - b.velocity;
        break;
      case "alpha":
        cmp = a.alpha - b.alpha;
        break;
      case "beta":
        cmp = a.beta - b.beta;
        break;
      case "config":
        cmp = a.config.localeCompare(b.config);
        break;
      case "status":
        cmp = a.status.localeCompare(b.status);
        break;
    }
    return dir === "asc" ? cmp : -cmp;
  });
  return sorted;
}

export function OperatingPointsPanel({
  points,
  isLoading,
  isGenerating,
  isTrimming,
  error,
  onGenerate,
  onTrimWithAvl,
  onTrimWithAerobuildup,
  controlSurfaces,
  onUpdateDeflections,
  onDeleteOp,
  onDeleteAll,
  onCreateOp,
}: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [selectedPoint, setSelectedPoint] =
    useState<StoredOperatingPoint | null>(null);
  const [avlConstraints, setAvlConstraints] = useState<TrimConstraint[]>([
    { variable: "elevator", target: "Cm", value: 0 },
  ]);
  const [abTrimVariable, setAbTrimVariable] = useState("elevator");
  const [abTargetCoefficient, setAbTargetCoefficient] = useState("CL");
  const [abTargetValue, setAbTargetValue] = useState("0.5");
  const [avlResult, setAvlResult] = useState<AVLTrimResult | null>(null);
  const [abResult, setAbResult] = useState<AeroBuildupTrimResult | null>(null);
  const [addDialogOpen, setAddDialogOpen] = useState(false);

  const handleSort = useCallback(
    (key: SortKey) => {
      if (sortKey === key) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortKey(key);
        setSortDir("asc");
      }
    },
    [sortKey],
  );

  const openDrawer = useCallback((pt: StoredOperatingPoint) => {
    setSelectedPoint(pt);
    setAvlResult(null);
    setAbResult(null);
  }, []);

  const closeDrawer = useCallback(() => {
    setSelectedPoint(null);
    setAvlResult(null);
    setAbResult(null);
  }, []);

  useEffect(() => {
    if (!selectedPoint) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeDrawer();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [selectedPoint, closeDrawer]);

  const handleAvlTrim = useCallback(async () => {
    if (!selectedPoint) return;
    const result = await onTrimWithAvl(selectedPoint, avlConstraints);
    setAvlResult(result);
  }, [selectedPoint, avlConstraints, onTrimWithAvl]);

  const handleAbTrim = useCallback(async () => {
    if (!selectedPoint) return;
    const val = parseFloat(abTargetValue);
    if (isNaN(val)) return;
    const result = await onTrimWithAerobuildup(
      selectedPoint,
      abTrimVariable,
      abTargetCoefficient,
      val,
    );
    setAbResult(result);
  }, [
    selectedPoint,
    abTrimVariable,
    abTargetCoefficient,
    abTargetValue,
    onTrimWithAerobuildup,
  ]);

  const updateConstraint = useCallback(
    (idx: number, field: keyof TrimConstraint, val: string) => {
      setAvlConstraints((prev) => {
        const next = [...prev];
        if (field === "value") {
          next[idx] = { ...next[idx], value: parseFloat(val) || 0 };
        } else {
          next[idx] = { ...next[idx], [field]: val };
        }
        return next;
      });
    },
    [],
  );

  const addConstraint = useCallback(() => {
    setAvlConstraints((prev) => [
      ...prev,
      { variable: "", target: "", value: 0 },
    ]);
  }, []);

  const removeConstraint = useCallback((idx: number) => {
    setAvlConstraints((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const sorted = useMemo(
    () => sortPoints(points, sortKey, sortDir),
    [points, sortKey, sortDir],
  );

  return (
    <div className="relative flex min-h-0 flex-1 flex-col gap-4 bg-card-muted p-6">
      <div className="flex items-center gap-3">
        <div className="flex-1" />
        {onCreateOp && (
          <button
            onClick={() => setAddDialogOpen(true)}
            disabled={isGenerating}
            className="flex items-center gap-1.5 rounded-full border border-border bg-card px-4 py-1.5 font-[family-name:var(--font-geist-sans)] text-[12px] font-medium text-foreground transition-colors hover:bg-sidebar-accent disabled:opacity-50"
            data-testid="add-op-button"
          >
            + Add OP
          </button>
        )}
        {onDeleteAll && points.length > 0 && (
          <button
            onClick={() => {
              if (confirm(`Delete all ${points.length} operating points?`)) {
                void onDeleteAll();
              }
            }}
            disabled={isGenerating}
            className="flex items-center gap-1.5 rounded-full border border-red-500/40 bg-card px-4 py-1.5 font-[family-name:var(--font-geist-sans)] text-[12px] font-medium text-red-400 transition-colors hover:bg-red-500/10 disabled:opacity-50"
            data-testid="delete-all-ops-button"
          >
            Clear All
          </button>
        )}
        <button
          onClick={() => onGenerate()}
          disabled={isGenerating}
          className="flex items-center gap-1.5 rounded-full bg-[#FF8400] px-4 py-1.5 font-[family-name:var(--font-geist-sans)] text-[12px] font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {isGenerating ? "Generating..." : "Generate Default OPs"}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-red-400">
            {error}
          </span>
        </div>
      )}

      {points.length === 0 && !isLoading && !isGenerating && !error && (
        <div className="flex flex-1 flex-col items-center justify-center gap-2">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-muted-foreground">
            No operating points. Click Generate Default OPs to create them.
          </span>
        </div>
      )}

      {isLoading && points.length === 0 && (
        <div className="flex flex-1 items-center justify-center">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
            Loading operating points...
          </span>
        </div>
      )}

      {points.length > 0 && (
        <div className="min-h-0 flex-1 overflow-auto rounded-xl border border-border bg-card">
          <table className="w-full">
            <thead className="sticky top-0 z-10 bg-card">
              <tr className="border-b border-border">
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className="cursor-pointer select-none px-4 py-2.5 text-left font-[family-name:var(--font-geist-sans)] text-[11px] font-medium uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground"
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.label}
                      {sortKey === col.key &&
                        (sortDir === "asc" ? (
                          <ChevronUp size={12} />
                        ) : (
                          <ChevronDown size={12} />
                        ))}
                    </span>
                  </th>
                ))}
                {onDeleteOp && <th className="w-10 px-2 py-2.5" />}
              </tr>
            </thead>
            <tbody>
              {sorted.map((pt) => {
                const style = STATUS_STYLES[pt.status];
                return (
                  <tr
                    key={pt.id}
                    onClick={() => openDrawer(pt)}
                    className="cursor-pointer border-b border-border transition-colors last:border-b-0 hover:bg-sidebar-accent"
                  >
                    <td className="px-4 py-2.5 font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
                      {pt.name}
                    </td>
                    <td className="px-4 py-2.5 font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
                      {pt.velocity.toFixed(1)}
                    </td>
                    <td className="px-4 py-2.5 font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
                      {(pt.alpha * RAD_TO_DEG).toFixed(2)}
                    </td>
                    <td className="px-4 py-2.5 font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
                      {(pt.beta * RAD_TO_DEG).toFixed(2)}
                    </td>
                    <td className="px-4 py-2.5 font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
                      {pt.config}
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-[family-name:var(--font-geist-sans)] text-[10px] font-medium ${style.bg} ${style.text}`}
                      >
                        {style.spinner && (
                          <Loader2 size={10} className="animate-spin" />
                        )}
                        {style.label}
                      </span>
                      {pt.trim_enrichment?.design_warnings?.some(
                        (w: { level: string }) => w.level === "warning" || w.level === "critical",
                      ) && (
                        <span
                          className="ml-1.5 inline-block size-2 rounded-full bg-yellow-500"
                          title="Has design warnings"
                        />
                      )}
                    </td>
                    {onDeleteOp && (
                      <td className="px-2 py-2.5">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (confirm(`Delete '${pt.name}'?`)) {
                              void onDeleteOp(pt.id);
                            }
                          }}
                          className="rounded p-1 text-muted-foreground hover:bg-red-500/10 hover:text-red-400"
                          aria-label={`Delete ${pt.name}`}
                          data-testid={`delete-op-${pt.id}`}
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <OpComparisonTable points={points} />

      {selectedPoint && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="flex-1 bg-black/40"
            onClick={closeDrawer}
            onKeyDown={(e) => {
              if (e.key === "Escape") closeDrawer();
            }}
            role="button"
            tabIndex={-1}
            aria-label="Close detail drawer"
          />
          <div className="flex h-full w-[480px] flex-col overflow-y-auto border-l border-border bg-card shadow-2xl">
            <div className="flex items-center justify-between border-b border-border px-6 py-4">
              <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
                {selectedPoint.name}
              </h2>
              <button
                onClick={closeDrawer}
                aria-label="Close"
                className="flex size-6 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
              >
                <X size={14} />
              </button>
            </div>

            <div className="flex flex-col gap-5 p-6">
              {selectedPoint.description && (
                <p className="font-[family-name:var(--font-geist-sans)] text-[13px] text-muted-foreground">
                  {selectedPoint.description}
                </p>
              )}

              <AnalysisGoalCard enrichment={selectedPoint.trim_enrichment ?? null} />
              <ControlAuthorityChart enrichment={selectedPoint.trim_enrichment ?? null} />
              <DesignWarningBadges enrichment={selectedPoint.trim_enrichment ?? null} />
              <MixerValuesCard enrichment={selectedPoint.trim_enrichment ?? null} />

              <div className="flex flex-col gap-3 rounded-xl border border-border bg-card-muted p-4">
                <span className="font-[family-name:var(--font-geist-sans)] text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  Flight Conditions
                </span>
                <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                  <DetailRow label="Velocity" value={`${selectedPoint.velocity.toFixed(2)} m/s`} />
                  <DetailRow label="Alpha" value={`${(selectedPoint.alpha * RAD_TO_DEG).toFixed(2)} deg`} />
                  <DetailRow label="Beta" value={`${(selectedPoint.beta * RAD_TO_DEG).toFixed(2)} deg`} />
                  <DetailRow label="Altitude" value={`${selectedPoint.altitude.toFixed(0)} m`} />
                  <DetailRow label="p" value={selectedPoint.p.toFixed(4)} />
                  <DetailRow label="q" value={selectedPoint.q.toFixed(4)} />
                  <DetailRow label="r" value={selectedPoint.r.toFixed(4)} />
                  <DetailRow label="Config" value={selectedPoint.config} />
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <span className="font-[family-name:var(--font-geist-sans)] text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  Status
                </span>
                <span
                  className={`inline-flex w-fit rounded-full px-2 py-0.5 font-[family-name:var(--font-geist-sans)] text-[10px] font-medium ${STATUS_STYLES[selectedPoint.status].bg} ${STATUS_STYLES[selectedPoint.status].text}`}
                >
                  {STATUS_STYLES[selectedPoint.status].label}
                </span>
              </div>

              {selectedPoint.warnings.length > 0 && (
                <div className="flex flex-col gap-1.5 rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-4 py-2">
                  <span className="font-[family-name:var(--font-geist-sans)] text-[11px] font-medium uppercase tracking-wider text-yellow-400">
                    Warnings
                  </span>
                  {selectedPoint.warnings.map((w, i) => (
                    <span
                      key={i}
                      className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-yellow-400"
                    >
                      {w}
                    </span>
                  ))}
                </div>
              )}

              <ControlDeflectionsSection
                controlSurfaces={controlSurfaces}
                currentDeflections={selectedPoint.control_deflections}
                trimControls={selectedPoint.controls}
                onSave={(deflections) =>
                  onUpdateDeflections(selectedPoint.id, deflections)
                }
                disabled={isTrimming}
              />

              {Object.keys(selectedPoint.controls).length > 0 && (
                <div className="flex flex-col gap-3 rounded-xl border border-border bg-card-muted p-4">
                  <span className="font-[family-name:var(--font-geist-sans)] text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                    Controls
                  </span>
                  <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                    {Object.entries(selectedPoint.controls).map(
                      ([key, val]) => (
                        <DetailRow
                          key={key}
                          label={key}
                          value={val.toFixed(4)}
                        />
                      ),
                    )}
                  </div>
                </div>
              )}

              <div className="flex flex-col gap-3 rounded-xl border border-border bg-card-muted p-4">
                <span className="font-[family-name:var(--font-geist-sans)] text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  Trim with AVL
                </span>
                {avlConstraints.map((c, i) => (
                  <div key={i} className="flex items-end gap-2">
                    <TrimInput
                      label="Variable"
                      value={c.variable}
                      onChange={(v) => updateConstraint(i, "variable", v)}
                    />
                    <TrimInput
                      label="Target"
                      value={c.target}
                      onChange={(v) => updateConstraint(i, "target", v)}
                    />
                    <TrimInput
                      label="Value"
                      value={String(c.value)}
                      type="number"
                      onChange={(v) => updateConstraint(i, "value", v)}
                    />
                    <button
                      onClick={() => removeConstraint(i)}
                      className="mb-0.5 flex size-6 flex-shrink-0 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
                    >
                      <X size={12} />
                    </button>
                  </div>
                ))}
                <div className="flex gap-2">
                  <button
                    onClick={addConstraint}
                    className="rounded-full border border-border px-3 py-1 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground transition-colors hover:text-foreground"
                  >
                    + Constraint
                  </button>
                  <div className="flex-1" />
                  <button
                    onClick={handleAvlTrim}
                    disabled={isTrimming || avlConstraints.length === 0}
                    className="rounded-full bg-[#FF8400] px-4 py-1 font-[family-name:var(--font-geist-sans)] text-[11px] font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                  >
                    {isTrimming ? "Trimming..." : "Run AVL Trim"}
                  </button>
                </div>
                {avlResult && <TrimResultCard result={avlResult} />}
              </div>

              <div className="flex flex-col gap-3 rounded-xl border border-border bg-card-muted p-4">
                <span className="font-[family-name:var(--font-geist-sans)] text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  Trim with AeroBuildup
                </span>
                <div className="flex flex-wrap gap-2">
                  <TrimInput
                    label="Trim Variable"
                    value={abTrimVariable}
                    onChange={setAbTrimVariable}
                  />
                  <TrimInput
                    label="Target Coefficient"
                    value={abTargetCoefficient}
                    onChange={setAbTargetCoefficient}
                  />
                  <TrimInput
                    label="Target Value"
                    value={abTargetValue}
                    type="number"
                    onChange={setAbTargetValue}
                  />
                </div>
                <div className="flex justify-end">
                  <button
                    onClick={handleAbTrim}
                    disabled={isTrimming}
                    className="rounded-full bg-[#FF8400] px-4 py-1 font-[family-name:var(--font-geist-sans)] text-[11px] font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                  >
                    {isTrimming ? "Trimming..." : "Run AeroBuildup Trim"}
                  </button>
                </div>
                {abResult && <AbTrimResultCard result={abResult} />}
              </div>
            </div>
          </div>
        </div>
      )}
      {addDialogOpen && onCreateOp && (
        <AddOpDialog
          onClose={() => setAddDialogOpen(false)}
          onCreate={async (payload) => {
            await onCreateOp(payload);
            setAddDialogOpen(false);
          }}
        />
      )}
    </div>
  );
}

function AddOpDialog({
  onClose,
  onCreate,
}: Readonly<{
  onClose: () => void;
  onCreate: (payload: {
    name: string;
    velocity: number;
    alpha: number;
    beta?: number;
    altitude?: number;
    config?: string;
  }) => Promise<void>;
}>) {
  const [name, setName] = useState("");
  const [velocity, setVelocity] = useState("18");
  const [alpha, setAlpha] = useState("0");
  const [beta, setBeta] = useState("0");
  const [altitude, setAltitude] = useState("0");
  const [config, setConfig] = useState("clean");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!name.trim()) return;
    setSubmitting(true);
    try {
      await onCreate({
        name: name.trim(),
        velocity: parseFloat(velocity) || 18,
        alpha: parseFloat(alpha) || 0,
        beta: parseFloat(beta) || 0,
        altitude: parseFloat(altitude) || 0,
        config,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-[420px] rounded-xl border border-border bg-card p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-[family-name:var(--font-geist-sans)] text-[14px] font-medium text-foreground">
            Add Operating Point
          </h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X size={16} />
          </button>
        </div>
        <div className="flex flex-col gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-wider text-muted-foreground">Name</span>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. high_speed_pass"
              className="rounded border border-border bg-card-muted px-2 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground outline-none focus:border-orange-400"
              data-testid="add-op-name"
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-1">
              <span className="text-[11px] uppercase tracking-wider text-muted-foreground">Velocity (m/s)</span>
              <input
                type="number"
                value={velocity}
                onChange={(e) => setVelocity(e.target.value)}
                className="rounded border border-border bg-card-muted px-2 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground outline-none focus:border-orange-400"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[11px] uppercase tracking-wider text-muted-foreground">Alpha (°)</span>
              <input
                type="number"
                value={alpha}
                onChange={(e) => setAlpha(e.target.value)}
                className="rounded border border-border bg-card-muted px-2 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground outline-none focus:border-orange-400"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[11px] uppercase tracking-wider text-muted-foreground">Beta (°)</span>
              <input
                type="number"
                value={beta}
                onChange={(e) => setBeta(e.target.value)}
                className="rounded border border-border bg-card-muted px-2 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground outline-none focus:border-orange-400"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[11px] uppercase tracking-wider text-muted-foreground">Altitude (m)</span>
              <input
                type="number"
                value={altitude}
                onChange={(e) => setAltitude(e.target.value)}
                className="rounded border border-border bg-card-muted px-2 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground outline-none focus:border-orange-400"
              />
            </label>
          </div>
          <label className="flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-wider text-muted-foreground">Config</span>
            <select
              value={config}
              onChange={(e) => setConfig(e.target.value)}
              className="rounded border border-border bg-card-muted px-2 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground outline-none focus:border-orange-400"
            >
              <option value="clean">clean</option>
              <option value="takeoff">takeoff</option>
              <option value="landing">landing</option>
            </select>
          </label>
          <div className="mt-2 flex justify-end gap-2">
            <button
              onClick={onClose}
              className="rounded-full border border-border px-3 py-1.5 text-[12px] text-muted-foreground hover:text-foreground"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={!name.trim() || submitting}
              className="rounded-full bg-[#FF8400] px-4 py-1.5 text-[12px] font-medium text-white hover:opacity-90 disabled:opacity-50"
              data-testid="add-op-submit"
            >
              {submitting ? "Creating..." : "Create"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function DetailRow({
  label,
  value,
}: Readonly<{ label: string; value: string }>) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-muted-foreground">
        {label}
      </span>
      <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground">
        {value}
      </span>
    </div>
  );
}

function TrimInput({
  label,
  value,
  type = "text",
  onChange,
}: Readonly<{
  label: string;
  value: string;
  type?: string;
  onChange: (v: string) => void;
}>) {
  return (
    <div className="flex flex-1 flex-col gap-1">
      <span className="text-[11px] text-muted-foreground">{label}</span>
      <input
        type={type}
        step={type === "number" ? "any" : undefined}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-border bg-input px-2.5 py-1.5 text-[12px] text-foreground outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
      />
    </div>
  );
}

function TrimResultCard({
  result,
}: Readonly<{ result: AVLTrimResult }>) {
  return (
    <div
      className={`mt-1 rounded-lg border p-3 ${result.converged ? "border-emerald-500/30 bg-emerald-500/10" : "border-red-500/30 bg-red-500/10"}`}
    >
      <div className="mb-2 flex items-center gap-2">
        <span
          className={`inline-flex rounded-full px-2 py-0.5 font-[family-name:var(--font-geist-sans)] text-[10px] font-medium ${result.converged ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"}`}
        >
          {result.converged ? "Converged" : "Not Converged"}
        </span>
      </div>
      {Object.keys(result.trimmed_deflections).length > 0 && (
        <div className="flex flex-col gap-1">
          <span className="font-[family-name:var(--font-geist-sans)] text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Trimmed Deflections
          </span>
          {Object.entries(result.trimmed_deflections).map(([k, v]) => (
            <div key={k} className="flex justify-between">
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
                {k}
              </span>
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground">
                {v.toFixed(4)}
              </span>
            </div>
          ))}
        </div>
      )}
      {Object.keys(result.aero_coefficients).length > 0 && (
        <div className="mt-2 flex flex-col gap-1">
          <span className="font-[family-name:var(--font-geist-sans)] text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Aero Coefficients
          </span>
          {Object.entries(result.aero_coefficients).map(([k, v]) => (
            <div key={k} className="flex justify-between">
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
                {k}
              </span>
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground">
                {v.toFixed(6)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function _findTrimDeflection(
  trimControls: Record<string, number> | null | undefined,
  surfaceName: string,
): number | null {
  if (!trimControls) return null;
  // Backend stores trim solution keyed as "[control_type]surface_name"
  // (e.g. "[elevator]elevator"). Match by the part after the closing
  // bracket so we find the value regardless of control_type.
  for (const [key, val] of Object.entries(trimControls)) {
    const match = key.match(/^\[[^\]]+\](.+)$/);
    if (match && match[1] === surfaceName) return val;
  }
  return null;
}

function ControlDeflectionsSection({
  controlSurfaces,
  currentDeflections,
  trimControls,
  onSave,
  disabled,
}: Readonly<{
  controlSurfaces: ControlSurface[];
  currentDeflections: Record<string, number> | null;
  trimControls?: Record<string, number> | null;
  onSave: (deflections: Record<string, number> | null) => void;
  disabled: boolean;
}>) {
  const [showInfo, setShowInfo] = useState(false);

  const initialDeflections = useMemo(() => {
    const initial: Record<string, string> = {};
    for (const cs of controlSurfaces) {
      // Priority order:
      // 1. User override (currentDeflections) — explicit choice wins
      // 2. Trim solution (trimControls) — solver result, the natural "current"
      // 3. Geometry default (cs.deflection_deg) — typically 0 for clean config
      const overrideValue = currentDeflections?.[cs.name];
      const trimValue = _findTrimDeflection(trimControls, cs.name);
      const fallback = trimValue != null ? trimValue : cs.deflection_deg;
      initial[cs.name] =
        overrideValue != null ? String(overrideValue) : String(fallback);
    }
    return initial;
  }, [controlSurfaces, currentDeflections, trimControls]);

  const [localDeflections, setLocalDeflections] = useState(initialDeflections);

  // Reset local state when inputs change by comparing the serialized key
  const deflectionKey = JSON.stringify(initialDeflections);
  const [prevKey, setPrevKey] = useState(deflectionKey);
  if (deflectionKey !== prevKey) {
    setPrevKey(deflectionKey);
    setLocalDeflections(initialDeflections);
  }

  const handleChange = useCallback((name: string, value: string) => {
    setLocalDeflections((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleSave = useCallback(() => {
    const deflections: Record<string, number> = {};
    for (const [name, val] of Object.entries(localDeflections)) {
      deflections[name] = parseFloat(val) || 0;
    }
    onSave(deflections);
  }, [localDeflections, onSave]);

  const handleReset = useCallback(() => {
    onSave(null);
  }, [onSave]);

  return (
    <div className="relative flex flex-col gap-3 rounded-xl border border-border bg-card-muted p-4">
      <div className="flex items-center gap-1.5">
        <span className="font-[family-name:var(--font-geist-sans)] text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          Control Deflections
        </span>
        <button
          type="button"
          onClick={() => setShowInfo((v) => !v)}
          className="text-muted-foreground hover:text-orange-400"
          aria-label="Sign convention for control deflections"
          data-testid="control-deflections-info"
        >
          <Info size={12} />
        </button>
      </div>
      {showInfo && (
        <div
          className="absolute left-4 top-10 z-20 max-w-[420px] whitespace-pre-line rounded-md border border-border bg-card px-3 py-2 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground shadow-lg"
          role="tooltip"
        >
          {"Sign convention (ASB / aerospace standard):\n" +
            "• Elevator / elevon: − = trailing-edge UP → nose-up moment\n" +
            "• Aileron: + = right-wing TE down (right roll)\n" +
            "• Rudder: + = trailing-edge LEFT → nose-left yaw\n\n" +
            "Values shown reflect the trim solution — edit to override " +
            "for what-if analysis."}
        </div>
      )}
      {controlSurfaces.length === 0 ? (
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          No control surfaces found
        </span>
      ) : (
        <>
          <div className="flex flex-col gap-2">
            {controlSurfaces.map((cs) => {
              const isOverridden =
                currentDeflections != null &&
                cs.name in currentDeflections &&
                currentDeflections[cs.name] !== cs.deflection_deg;
              return (
                <div key={cs.name} className="flex items-center gap-3">
                  <span
                    className={`flex-1 font-[family-name:var(--font-geist-sans)] text-[12px] ${
                      isOverridden
                        ? "text-[#FF8400]"
                        : "text-muted-foreground"
                    }`}
                  >
                    {isOverridden && (
                      <span className="mr-1.5 inline-block size-1.5 rounded-full bg-[#FF8400]" />
                    )}
                    {cs.name}
                  </span>
                  <input
                    type="number"
                    step="any"
                    value={localDeflections[cs.name] ?? "0"}
                    onChange={(e) => handleChange(cs.name, e.target.value)}
                    disabled={disabled}
                    className={`w-24 rounded-lg border border-border bg-input px-2.5 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[12px] outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none ${
                      isOverridden ? "text-[#FF8400]" : "text-foreground"
                    } disabled:opacity-50`}
                    aria-label={`${cs.name} deflection`}
                  />
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
                    deg
                  </span>
                </div>
              );
            })}
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleReset}
              disabled={disabled || currentDeflections == null}
              className="rounded-full border border-border px-3 py-1 font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
            >
              Reset to Defaults
            </button>
            <div className="flex-1" />
            <button
              onClick={handleSave}
              disabled={disabled}
              className="rounded-full bg-[#FF8400] px-4 py-1 font-[family-name:var(--font-geist-sans)] text-[11px] font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              Save Deflections
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function AbTrimResultCard({
  result,
}: Readonly<{ result: AeroBuildupTrimResult }>) {
  return (
    <div
      className={`mt-1 rounded-lg border p-3 ${result.converged ? "border-emerald-500/30 bg-emerald-500/10" : "border-red-500/30 bg-red-500/10"}`}
    >
      <div className="mb-2 flex items-center gap-2">
        <span
          className={`inline-flex rounded-full px-2 py-0.5 font-[family-name:var(--font-geist-sans)] text-[10px] font-medium ${result.converged ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"}`}
        >
          {result.converged ? "Converged" : "Not Converged"}
        </span>
      </div>
      <div className="flex flex-col gap-1">
        <div className="flex justify-between">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
            {result.trim_variable}
          </span>
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground">
            {result.trimmed_deflection.toFixed(4)}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
            {result.target_coefficient}
          </span>
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground">
            {result.achieved_value != null
              ? result.achieved_value.toFixed(6)
              : "N/A"}
          </span>
        </div>
      </div>
      {Object.keys(result.aero_coefficients).length > 0 && (
        <div className="mt-2 flex flex-col gap-1">
          <span className="font-[family-name:var(--font-geist-sans)] text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Aero Coefficients
          </span>
          {Object.entries(result.aero_coefficients).map(([k, v]) => (
            <div key={k} className="flex justify-between">
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
                {k}
              </span>
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground">
                {v.toFixed(6)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

