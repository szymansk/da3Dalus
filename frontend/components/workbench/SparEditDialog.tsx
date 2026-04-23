"use client";

import { useState, useEffect } from "react";
import { X } from "lucide-react";
import { API_BASE } from "@/lib/fetcher";

const SPAR_MODES = ["standard", "follow", "normal", "standard_backward", "orthogonal_backward"] as const;

interface SparEditDialogProps {
  open: boolean;
  onClose: () => void;
  aeroplaneId: string;
  wingName: string;
  xsecIndex: number;
  sparIndex?: number;  // undefined = create new, number = edit existing
  initialData?: {
    spare_position_factor: number;
    spare_support_dimension_width: number;
    spare_support_dimension_height: number;
    spare_mode: string;
    spare_start: number;
    spare_length?: number;
    spare_vector?: number[] | null;
    spare_origin?: number[] | null;
  };
  onSaved: () => void;
}

function applyOptionalVec3(
  vec: number[] | null | undefined,
  setX: (v: string) => void,
  setY: (v: string) => void,
  setZ: (v: string) => void,
) {
  setX(vec?.[0] == null ? "" : String(vec[0]));
  setY(vec?.[1] == null ? "" : String(vec[1]));
  setZ(vec?.[2] == null ? "" : String(vec[2]));
}

function num(v: string, fallback = 0): number {
  if (v === "" || v === "-" || v === ".") return fallback;
  const n = Number.parseFloat(v);
  return Number.isNaN(n) ? fallback : n;
}

export function SparEditDialog({
  open,
  onClose,
  aeroplaneId,
  wingName,
  xsecIndex,
  sparIndex,
  initialData,
  onSaved,
}: Readonly<SparEditDialogProps>) {
  const isNew = sparIndex === undefined;

  const [posFactor, setPosFactor] = useState("25");
  const [width, setWidth] = useState("4.42");
  const [height, setHeight] = useState("4.42");
  const [sparMode, setSparMode] = useState("standard");
  const [sparStart, setSparStart] = useState("0");
  const [sparLength, setSparLength] = useState("");
  const [vecX, setVecX] = useState("");
  const [vecY, setVecY] = useState("");
  const [vecZ, setVecZ] = useState("");
  const [origX, setOrigX] = useState("");
  const [origY, setOrigY] = useState("");
  const [origZ, setOrigZ] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialData) {
      setPosFactor(String((initialData.spare_position_factor ?? 0) * 100));
      setWidth(String(initialData.spare_support_dimension_width ?? 4.42));
      setHeight(String(initialData.spare_support_dimension_height ?? 4.42));
      setSparMode(initialData.spare_mode ?? "standard");
      setSparStart(String(initialData.spare_start ?? 0));
      setSparLength(initialData.spare_length == null ? "" : String(initialData.spare_length));
      applyOptionalVec3(initialData.spare_vector, setVecX, setVecY, setVecZ);
      applyOptionalVec3(initialData.spare_origin, setOrigX, setOrigY, setOrigZ);
    } else {
      setPosFactor("25");
      setWidth("4.42");
      setHeight("4.42");
      setSparMode("standard");
      setSparStart("0");
      setSparLength("");
      setVecX(""); setVecY(""); setVecZ("");
      setOrigX(""); setOrigY(""); setOrigZ("");
    }
    setError(null);
  }, [initialData, open]);

  if (!open) return null;

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = {
        spare_position_factor: num(posFactor) / 100,
        spare_support_dimension_width: num(width),
        spare_support_dimension_height: num(height),
        spare_mode: sparMode,
        spare_start: num(sparStart),
      };
      if (sparLength.trim()) {
        payload.spare_length = num(sparLength);
      }
      if (vecX.trim() && vecY.trim() && vecZ.trim()) {
        payload.spare_vector = [num(vecX), num(vecY), num(vecZ)];
      } else {
        payload.spare_vector = null;
      }
      if (origX.trim() && origY.trim() && origZ.trim()) {
        payload.spare_origin = [num(origX), num(origY), num(origZ)];
      } else {
        payload.spare_origin = null;
      }

      const url = isNew
        ? `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${xsecIndex}/spars`
        : `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${xsecIndex}/spars/${sparIndex}`;
      const method = isNew ? "POST" : "PUT";

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
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
    if (sparIndex === undefined) return;
    if (!confirm("Delete this spar?")) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${xsecIndex}/spars/${sparIndex}`,
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

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        className="flex max-h-[85vh] w-[420px] flex-col gap-4 overflow-y-auto rounded-2xl border border-border bg-card p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
            {isNew ? "Add Spar" : "Edit Spar"}
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
            <DialogField label="Position" value={posFactor} suffix="%" onChange={setPosFactor} />
            <div className="flex flex-1 flex-col gap-1">
              <label className="text-[11px] text-muted-foreground">Mode</label>
              <select
                value={sparMode}
                onChange={(e) => setSparMode(e.target.value)}
                className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
              >
                {SPAR_MODES.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex gap-3">
            <DialogField label="Width" value={width} suffix="mm" onChange={setWidth} />
            <DialogField label="Height" value={height} suffix="mm" onChange={setHeight} />
          </div>
          <div className="flex gap-3">
            <DialogField label="Start" value={sparStart} suffix="mm" onChange={setSparStart} />
            <DialogField label="Length (opt.)" value={sparLength} suffix="mm" onChange={setSparLength} />
          </div>
          <label className="pt-1 text-[11px] text-muted-foreground">Vector (opt.)</label>
          <div className="flex gap-3">
            <DialogField label="X" value={vecX} onChange={setVecX} />
            <DialogField label="Y" value={vecY} onChange={setVecY} />
            <DialogField label="Z" value={vecZ} onChange={setVecZ} />
          </div>
          <label className="pt-1 text-[11px] text-muted-foreground">Origin (opt.)</label>
          <div className="flex gap-3">
            <DialogField label="X" value={origX} onChange={setOrigX} />
            <DialogField label="Y" value={origY} onChange={setOrigY} />
            <DialogField label="Z" value={origZ} onChange={setOrigZ} />
          </div>
        </div>

        {/* Error */}
        {error && <p className="text-[12px] text-red-500">{error}</p>}

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2">
          {!isNew && (
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
            {saving ? "Saving..." : isNew ? "Add" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}

function DialogField({
  label,
  value,
  suffix,
  onChange,
}: {
  label: string;
  value: string;
  suffix?: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-1 flex-col gap-1">
      <label className="text-[11px] text-muted-foreground">{label}</label>
      <div className="flex items-center gap-2 rounded-xl border border-border bg-input px-3 py-2">
        <input
          type="number"
          step="any"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full bg-transparent text-[13px] text-foreground outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
        />
        {suffix && (
          <span className="flex-shrink-0 text-[11px] text-muted-foreground">{suffix}</span>
        )}
      </div>
    </div>
  );
}
