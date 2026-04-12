"use client";

import { useEffect, useState } from "react";
import { useAeroplaneContext } from "./AeroplaneContext";
import { useWing, type XSec } from "@/hooks/useWings";

interface LocalXSecState {
  airfoil: string;
  chord: number;      // stored in mm for display
  twist: number;
  xyz_le: [number, number, number];
}

function xsecToLocal(xsec: XSec): LocalXSecState {
  return {
    airfoil: xsec.airfoil,
    chord: xsec.chord * 1000,   // meters -> mm
    twist: xsec.twist,
    xyz_le: [xsec.xyz_le[0], xsec.xyz_le[1], xsec.xyz_le[2]],
  };
}

function localToPayload(local: LocalXSecState): Partial<XSec> {
  return {
    airfoil: local.airfoil,
    chord: local.chord / 1000,   // mm -> meters
    twist: local.twist,
    xyz_le: [...local.xyz_le],
  };
}

export function PropertyForm() {
  const { aeroplaneId, selectedWing, selectedXsecIndex } =
    useAeroplaneContext();
  const { wing, updateXSec, mutate } = useWing(aeroplaneId, selectedWing);

  const xsec =
    wing && selectedXsecIndex !== null
      ? wing.x_secs[selectedXsecIndex] ?? null
      : null;

  const [local, setLocal] = useState<LocalXSecState | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync local state when the selected xsec changes
  useEffect(() => {
    if (xsec) {
      setLocal(xsecToLocal(xsec));
    } else {
      setLocal(null);
    }
    setError(null);
  }, [xsec?.airfoil, xsec?.chord, xsec?.twist, xsec?.xyz_le?.[0], xsec?.xyz_le?.[1], xsec?.xyz_le?.[2], selectedXsecIndex]);

  // No segment selected
  if (selectedXsecIndex === null || !xsec || !local) {
    return (
      <div className="rounded-[--radius-m] border border-border bg-card p-2.5 px-4">
        <p className="py-6 text-center text-[12px] text-muted-foreground">
          Select a segment in the tree
        </p>
      </div>
    );
  }

  function updateField<K extends keyof LocalXSecState>(
    key: K,
    value: LocalXSecState[K],
  ) {
    setLocal((prev) => (prev ? { ...prev, [key]: value } : prev));
    setError(null);
  }

  function updateXyzLe(axis: 0 | 1 | 2, value: number) {
    setLocal((prev) => {
      if (!prev) return prev;
      const next: [number, number, number] = [...prev.xyz_le];
      next[axis] = value;
      return { ...prev, xyz_le: next };
    });
    setError(null);
  }

  function handleCancel() {
    setLocal(xsecToLocal(xsec!));
    setError(null);
  }

  async function handleSave() {
    if (!local) return;
    setSaving(true);
    setError(null);
    try {
      await updateXSec(selectedXsecIndex!, localToPayload(local));
      await mutate();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-[--radius-m] border border-border bg-card p-2.5 px-4">
      {/* Header */}
      <div className="mb-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          segment {selectedXsecIndex} &middot; Properties
        </span>
      </div>

      {/* Field grid */}
      <div className="flex flex-col gap-3">
        {/* Row 1: airfoil | chord */}
        <div className="flex gap-3">
          <div className="flex flex-1 flex-col gap-1">
            <label className="text-[11px] text-muted-foreground">airfoil</label>
            <div className="flex items-center gap-2 rounded-[--radius-s] border border-border bg-input px-3 py-2">
              <input
                type="text"
                value={local.airfoil}
                onChange={(e) => updateField("airfoil", e.target.value)}
                className="w-full bg-transparent text-[13px] text-foreground outline-none"
              />
            </div>
          </div>
          <div className="flex flex-1 flex-col gap-1">
            <label className="text-[11px] text-muted-foreground">chord</label>
            <div className="flex items-center gap-2 rounded-[--radius-s] border border-border bg-input px-3 py-2">
              <input
                type="number"
                step="any"
                value={local.chord}
                onChange={(e) => updateField("chord", parseFloat(e.target.value) || 0)}
                className="w-full bg-transparent text-[13px] text-foreground outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
              />
              <span className="text-[11px] text-muted-foreground">mm</span>
            </div>
          </div>
        </div>

        {/* Row 2: twist | x_sec_type (read-only) */}
        <div className="flex gap-3">
          <div className="flex flex-1 flex-col gap-1">
            <label className="text-[11px] text-muted-foreground">twist</label>
            <div className="flex items-center gap-2 rounded-[--radius-s] border border-border bg-input px-3 py-2">
              <input
                type="number"
                step="any"
                value={local.twist}
                onChange={(e) => updateField("twist", parseFloat(e.target.value) || 0)}
                className="w-full bg-transparent text-[13px] text-foreground outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
              />
              <span className="text-[11px] text-muted-foreground">&deg;</span>
            </div>
          </div>
          <div className="flex flex-1 flex-col gap-1">
            <label className="text-[11px] text-muted-foreground">x_sec_type</label>
            <div className="flex items-center gap-2 rounded-[--radius-s] border border-border bg-input px-3 py-2">
              <span className="text-[13px] text-foreground">
                {xsec.x_sec_type ?? "\u2014"}
              </span>
            </div>
          </div>
        </div>

        {/* Row 3: xyz_le (x, y, z) */}
        <div className="flex gap-3">
          {(["x", "y", "z"] as const).map((axis, i) => (
            <div key={axis} className="flex flex-1 flex-col gap-1">
              <label className="text-[11px] text-muted-foreground">
                xyz_le.{axis}
              </label>
              <div className="flex items-center gap-2 rounded-[--radius-s] border border-border bg-input px-3 py-2">
                <input
                  type="number"
                  step="any"
                  value={local.xyz_le[i]}
                  onChange={(e) =>
                    updateXyzLe(i as 0 | 1 | 2, parseFloat(e.target.value) || 0)
                  }
                  className="w-full bg-transparent text-[13px] text-foreground outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                />
                <span className="text-[11px] text-muted-foreground">m</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-col items-end gap-2 pt-4">
        <div className="flex gap-2">
          <button
            onClick={handleCancel}
            disabled={saving}
            className="rounded-[--radius-pill] border border-border-strong bg-background px-3.5 py-2 text-[13px] text-foreground hover:bg-sidebar-accent disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-[--radius-pill] bg-primary px-4 py-2 text-[13px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {saving ? "Saving\u2026" : "Save"}
          </button>
        </div>
        {error && (
          <p className="text-[12px] text-red-500">{error}</p>
        )}
      </div>
    </div>
  );
}
