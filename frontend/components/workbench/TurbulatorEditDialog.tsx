"use client";

import { useState, useEffect, useId } from "react";
import { X } from "lucide-react";
import { API_BASE } from "@/lib/fetcher";
import { useDialog } from "@/hooks/useDialog";

const TURBULATOR_FORMS = ["zigzag", "dots", "thread"] as const;
type TurbulatorForm = (typeof TURBULATOR_FORMS)[number];

type OptimizeScope = "section" | "segment" | "whole";

interface OptimizeSectionResult {
  y_m: number;
  chord_m: number;
  re_local: number;
  cl: number;
  xtr_opt: number;
  cd_clean: number;
  cd_tripped: number;
  delta_cd: number;
  warnings: string[];
}

interface OptimizeSummary {
  delta_cd0: number;
  l_d_clean: number;
  l_d_tripped: number;
  delta_l_d: number;
}

interface OptimizeResult {
  sections: OptimizeSectionResult[];
  summary: OptimizeSummary;
  scope: string;
}

export interface TurbulatorEditDialogProps {
  open: boolean;
  onClose: () => void;
  aeroplaneId: string;
  wingName: string;
  xsecIndex: number;
  isNew: boolean;
  initialData?: Record<string, unknown> | null;
  onSaved: () => void;
}

/** Safely convert a value to string, avoiding [object Object]. */
function safeStr(v: unknown, fallback = ""): string {
  if (v == null) return fallback;
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return JSON.stringify(v);
}

function optFloat(v: string): number | undefined {
  const trimmed = v.trim();
  if (!trimmed) return undefined;
  const n = Number.parseFloat(trimmed);
  return Number.isFinite(n) ? n : undefined;
}

export function TurbulatorEditDialog({
  open,
  onClose,
  aeroplaneId,
  wingName,
  xsecIndex,
  isNew,
  initialData,
  onSaved,
}: Readonly<TurbulatorEditDialogProps>) {
  const [form, setForm] = useState<TurbulatorForm>("zigzag");
  const [heightMm, setHeightMm] = useState("0.3");
  const [positionRoot, setPositionRoot] = useState("0.1");
  const [positionTip, setPositionTip] = useState("");
  const [enabled, setEnabled] = useState(true);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Optimize state
  const [optimizing, setOptimizing] = useState(false);
  const [optimizeScope, setOptimizeScope] = useState<OptimizeScope>("whole");
  const [optimizeResult, setOptimizeResult] = useState<OptimizeResult | null>(null);
  const [optimizeError, setOptimizeError] = useState<string | null>(null);

  const { dialogRef, handleClose } = useDialog(open, onClose);

  useEffect(() => {
    if (initialData && typeof initialData === "object") {
      const t = initialData;
      setForm((t.form as TurbulatorForm) ?? "zigzag");
      setHeightMm(safeStr(t.height_mm, "0.3"));
      setPositionRoot(safeStr(t.position_root, "0.1"));
      setPositionTip(t.position_tip != null ? safeStr(t.position_tip) : "");
      setEnabled(t.enabled !== false);
    } else {
      setForm("zigzag");
      setHeightMm("0.3");
      setPositionRoot("0.1");
      setPositionTip("");
      setEnabled(true);
    }
    setError(null);
    setOptimizeResult(null);
    setOptimizeError(null);
  }, [initialData, open]);

  function validate(): string | null {
    const root = optFloat(positionRoot);
    if (root == null || root < 0 || root > 1) return "Position root must be between 0 and 1.";
    const tip = optFloat(positionTip);
    if (tip !== undefined && (tip < 0 || tip > 1)) return "Position tip must be between 0 and 1.";
    const h = optFloat(heightMm);
    if (h !== undefined && h < 0) return "Height must be non-negative.";
    return null;
  }

  async function handleSave() {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = {
        form,
        height_mm: Number.parseFloat(heightMm) || 0.3,
        position_root: Number.parseFloat(positionRoot),
        enabled,
      };
      const tipVal = optFloat(positionTip);
      if (tipVal !== undefined) {
        payload.position_tip = tipVal;
      } else {
        payload.position_tip = null;
      }

      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${xsecIndex}/turbulator`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`${res.status}: ${text}`);
      }
      onSaved();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Delete this turbulator?")) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${xsecIndex}/turbulator`,
        { method: "DELETE" },
      );
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`${res.status}: ${text}`);
      }
      onSaved();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleOptimize() {
    setOptimizing(true);
    setOptimizeError(null);
    setOptimizeResult(null);
    try {
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/turbulator/optimize`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scope: optimizeScope }),
        },
      );
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`${res.status}: ${text}`);
      }
      const result: OptimizeResult = await res.json();
      setOptimizeResult(result);

      // Auto-apply optimal position if it helps (ΔL/D > 0)
      if (result.summary.delta_l_d <= 0) {
        // Turbulator would hurt or give no benefit — inform user but don't apply
        return;
      }

      if (result.sections.length > 0) {
        // For scope "whole": use the representative section nearest xsecIndex
        // For all scopes: use the median xtr_opt as the position root
        const representative = result.sections[Math.floor(result.sections.length / 2)];
        const firstSection = result.sections[0];
        const lastSection = result.sections[result.sections.length - 1];

        if (optimizeScope === "whole") {
          // Use representative section xtr_opt for both root and tip
          setPositionRoot(representative.xtr_opt.toFixed(3));
          setPositionTip(representative.xtr_opt.toFixed(3));
        } else {
          // section/segment: map first section → root, last → tip
          setPositionRoot(firstSection.xtr_opt.toFixed(3));
          if (result.sections.length > 1) {
            setPositionTip(lastSection.xtr_opt.toFixed(3));
          }
        }
      }
    } catch (err: unknown) {
      setOptimizeError(err instanceof Error ? err.message : "Optimization failed");
    } finally {
      setOptimizing(false);
    }
  }

  const hasTurbulator = !isNew;
  let submitLabel = "Save";
  if (saving) submitLabel = "Saving...";
  else if (isNew) submitLabel = "Add";

  return (
    <dialog
      ref={dialogRef}
      className="m-auto bg-transparent backdrop:bg-black/60"
      onClose={handleClose}
      aria-label={isNew ? "Add Turbulator" : "Edit Turbulator"}
    >
      <div className="flex max-h-[85vh] w-[480px] flex-col gap-4 overflow-y-auto rounded-2xl border border-border bg-card p-6 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
            {isNew ? "Add Turbulator" : "Edit Turbulator"}
          </h2>
          <button
            onClick={onClose}
            className="flex size-6 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
          >
            <X size={14} />
          </button>
        </div>

        {/* Fields */}
        <div className="flex flex-col gap-3">
          <div className="flex gap-3">
            <div className="flex flex-1 flex-col gap-1">
              <label htmlFor="turb-form" className="text-[11px] text-muted-foreground">Form</label>
              <select
                id="turb-form"
                value={form}
                onChange={(e) => setForm(e.target.value as TurbulatorForm)}
                className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
              >
                {TURBULATOR_FORMS.map((f) => (
                  <option key={f} value={f}>{f.charAt(0).toUpperCase() + f.slice(1)}</option>
                ))}
              </select>
            </div>
            <TurbulatorField label="Height (mm)" value={heightMm} onChange={setHeightMm} />
          </div>

          <div className="flex gap-3">
            <TurbulatorField
              label="Position root (x/c)"
              value={positionRoot}
              onChange={setPositionRoot}
              placeholder="0.1"
            />
            <TurbulatorField
              label="Position tip (x/c)"
              value={positionTip}
              onChange={setPositionTip}
              placeholder="same as root"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              id="turb-enabled"
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="turb-enabled" className="text-[11px] text-muted-foreground">Enabled</label>
          </div>

          {/* Optimize section */}
          <div className="border-t border-border pt-3">
            <p className="mb-2 text-[11px] text-muted-foreground">
              Optimize trip position for minimum drag at design speed:
            </p>
            <div className="flex items-center gap-2">
              <div className="flex flex-1 flex-col gap-1">
                <label htmlFor="turb-optimize-scope" className="text-[11px] text-muted-foreground">Scope</label>
                <select
                  id="turb-optimize-scope"
                  value={optimizeScope}
                  onChange={(e) => setOptimizeScope(e.target.value as OptimizeScope)}
                  className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
                >
                  <option value="section">Section</option>
                  <option value="segment">Segment</option>
                  <option value="whole">Whole wing</option>
                </select>
              </div>
              <button
                onClick={handleOptimize}
                disabled={optimizing || saving}
                className="mt-4 rounded-full border border-border px-4 py-2 text-[13px] text-foreground hover:bg-sidebar-accent disabled:opacity-50"
              >
                {optimizing ? "Optimizing…" : "Optimize"}
              </button>
            </div>

            {/* Optimize results */}
            {optimizeResult && (
              <div className="mt-3 rounded-xl border border-border bg-background p-3 text-[12px]">
                {optimizeResult.summary.delta_l_d <= 0 ? (
                  <p className="text-amber-400">
                    No benefit at this operating point — turbulator trip would reduce L/D
                    ({optimizeResult.summary.delta_l_d.toFixed(2)}). Position not applied.
                  </p>
                ) : (
                  <>
                    <p className="text-[#30A46C] font-medium">
                      Optimal position applied — ΔL/D: +{optimizeResult.summary.delta_l_d.toFixed(2)}
                    </p>
                    <div className="mt-1 flex gap-4 text-muted-foreground">
                      <span>L/D clean: {optimizeResult.summary.l_d_clean.toFixed(1)}</span>
                      <span>L/D tripped: {optimizeResult.summary.l_d_tripped.toFixed(1)}</span>
                    </div>
                    {optimizeResult.sections.some((s) => s.warnings.length > 0) && (
                      <div className="mt-2 border-t border-border pt-2 text-amber-400">
                        {optimizeResult.sections
                          .filter((s) => s.warnings.length > 0)
                          .map((s, i) => (
                            <p key={i}>
                              y={s.y_m.toFixed(3)} m: {s.warnings.join("; ")}
                            </p>
                          ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
            {optimizeError && (
              <p className="mt-2 text-[12px] text-red-500">{optimizeError}</p>
            )}
          </div>
        </div>

        {/* Error */}
        {error && <p className="text-[12px] text-red-500">{error}</p>}

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2">
          {hasTurbulator && (
            <button
              onClick={handleDelete}
              disabled={saving}
              className="rounded-full border border-destructive px-3 py-2 text-[13px] text-destructive hover:bg-destructive/10 disabled:opacity-50"
            >
              Delete
            </button>
          )}
          <span className="flex-1" />
          <button
            onClick={onClose}
            disabled={saving}
            className="rounded-full border border-border-strong bg-background px-3.5 py-2 text-[13px] text-foreground hover:bg-sidebar-accent disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-full bg-primary px-4 py-2 text-[13px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {submitLabel}
          </button>
        </div>
      </div>
    </dialog>
  );
}

function TurbulatorField({
  label,
  value,
  onChange,
  placeholder,
}: Readonly<{
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}>) {
  const id = useId();
  return (
    <div className="flex flex-1 flex-col gap-1">
      <label htmlFor={id} className="text-[11px] text-muted-foreground">{label}</label>
      <div className="flex items-center gap-2 rounded-xl border border-border bg-input px-3 py-2">
        <input
          id={id}
          type="number"
          step="any"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full bg-transparent text-[13px] text-foreground outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
        />
      </div>
    </div>
  );
}
