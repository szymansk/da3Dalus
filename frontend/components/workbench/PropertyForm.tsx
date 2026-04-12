"use client";

import { useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useAeroplaneContext } from "./AeroplaneContext";
import { useWing, type XSec } from "@/hooks/useWings";
import { API_BASE } from "@/lib/fetcher";

// ── Types ───────────────────────────────────────────────────────

type Mode = "wingconfig" | "asb";

interface WingConfigState {
  root_airfoil: string;
  root_chord: number;       // mm
  root_dihedral: number;    // degrees
  root_incidence: number;   // degrees
  root_rotation_point: number;
  tip_airfoil: string;
  tip_chord: number;        // mm
  tip_dihedral: number;
  tip_incidence: number;
  tip_rotation_point: number;
  length: number;           // mm
  sweep: number;            // mm
  number_interpolation_points: number;
  tip_type: string;
}

interface AsbState {
  airfoil: string;
  chord: number;            // display in mm (stored in m)
  twist: number;            // degrees
  xyz_le: [number, number, number]; // meters
}

// ── Converters ──────────────────────────────────────────────────

function xsecToAsb(xsec: XSec): AsbState {
  return {
    airfoil: xsec.airfoil,
    chord: xsec.chord * 1000,
    twist: xsec.twist,
    xyz_le: [xsec.xyz_le[0], xsec.xyz_le[1], xsec.xyz_le[2]],
  };
}

function asbToPayload(asb: AsbState): Partial<XSec> {
  return {
    airfoil: asb.airfoil,
    chord: asb.chord / 1000,
    twist: asb.twist,
    xyz_le: [...asb.xyz_le],
  };
}

function xsecsToWingConfig(
  xsecs: XSec[],
  segIndex: number,
): WingConfigState | null {
  if (segIndex < 0 || segIndex >= xsecs.length - 1) return null;
  const root = xsecs[segIndex];
  const tip = xsecs[segIndex + 1];
  const rootChord = root.chord * 1000;
  const tipChord = tip.chord * 1000;
  const dx = (tip.xyz_le[0] - root.xyz_le[0]) * 1000;
  const dy = (tip.xyz_le[1] - root.xyz_le[1]) * 1000;

  return {
    root_airfoil: root.airfoil,
    root_chord: rootChord,
    root_dihedral: 0, // cannot reverse-compute from xyz_le without full context
    root_incidence: root.twist,
    root_rotation_point: 0.25,
    tip_airfoil: tip.airfoil,
    tip_chord: tipChord,
    tip_dihedral: 0,
    tip_incidence: tip.twist,
    tip_rotation_point: 0.25,
    length: Math.abs(dy),
    sweep: dx,
    number_interpolation_points: root.number_interpolation_points ?? 201,
    tip_type: root.tip_type ?? "",
  };
}

// ── Field Component ─────────────────────────────────────────────

function Field({
  label,
  value,
  suffix,
  type = "number",
  onChange,
  readOnly,
  isSelect,
}: {
  label: string;
  value: string | number;
  suffix?: string;
  type?: "text" | "number";
  onChange?: (v: string) => void;
  readOnly?: boolean;
  isSelect?: boolean;
}) {
  return (
    <div className="flex flex-1 flex-col gap-1">
      <label className="text-[11px] text-muted-foreground">{label}</label>
      <div className="flex items-center gap-2 rounded-[--radius-s] border border-border bg-input px-3 py-2">
        {readOnly ? (
          <span className="text-[13px] text-foreground">{value}</span>
        ) : (
          <input
            type={type}
            step="any"
            value={value}
            onChange={(e) => onChange?.(e.target.value)}
            className="w-full bg-transparent text-[13px] text-foreground outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
          />
        )}
        <span className="flex-shrink-0">
          {isSelect && (
            <ChevronDown size={12} className="text-muted-foreground" />
          )}
          {suffix && (
            <span className="text-[11px] text-muted-foreground">{suffix}</span>
          )}
        </span>
      </div>
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────

export function PropertyForm() {
  const { aeroplaneId, selectedWing, selectedXsecIndex } =
    useAeroplaneContext();
  const { wing, updateXSec, mutate } = useWing(aeroplaneId, selectedWing);

  const [mode, setMode] = useState<Mode>("wingconfig");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ASB state
  const xsec =
    wing && selectedXsecIndex !== null
      ? wing.x_secs[selectedXsecIndex] ?? null
      : null;
  const [asb, setAsb] = useState<AsbState | null>(null);

  // WingConfig state
  const [wc, setWc] = useState<WingConfigState | null>(null);

  // Sync state when selection changes
  useEffect(() => {
    if (xsec) {
      setAsb(xsecToAsb(xsec));
    } else {
      setAsb(null);
    }
    if (wing && selectedXsecIndex !== null) {
      setWc(xsecsToWingConfig(wing.x_secs, selectedXsecIndex));
    } else {
      setWc(null);
    }
    setError(null);
  }, [xsec?.airfoil, xsec?.chord, xsec?.twist, selectedXsecIndex, wing]);

  // No segment selected
  if (selectedXsecIndex === null || !xsec) {
    return (
      <div className="rounded-[--radius-m] border border-border bg-card p-2.5 px-4">
        <p className="py-6 text-center text-[12px] text-muted-foreground">
          Select a segment in the tree
        </p>
      </div>
    );
  }

  function handleCancel() {
    if (xsec) setAsb(xsecToAsb(xsec));
    if (wing && selectedXsecIndex !== null)
      setWc(xsecsToWingConfig(wing.x_secs, selectedXsecIndex));
    setError(null);
  }

  async function handleSaveAsb() {
    if (!asb) return;
    setSaving(true);
    setError(null);
    try {
      await updateXSec(selectedXsecIndex!, asbToPayload(asb));
      await mutate();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveWingConfig() {
    if (!wc || !aeroplaneId || !selectedWing || !wing) return;
    setSaving(true);
    setError(null);
    try {
      // Build a WingConfiguration JSON from the current wing + edited segment
      const segments = wing.x_secs.slice(0, -1).map((rootXsec, i) => {
        const tipXsec = wing.x_secs[i + 1];
        const isEdited = i === selectedXsecIndex;
        const src = isEdited ? wc : null;

        return {
          root_airfoil: {
            airfoil: src?.root_airfoil ?? rootXsec.airfoil,
            chord: src?.root_chord ?? rootXsec.chord * 1000,
            dihedral_as_rotation_in_degrees: src?.root_dihedral ?? 0,
            incidence: src?.root_incidence ?? rootXsec.twist,
            rotation_point_rel_chord: src?.root_rotation_point ?? 0.25,
          },
          tip_airfoil: {
            airfoil: src?.tip_airfoil ?? tipXsec.airfoil,
            chord: src?.tip_chord ?? tipXsec.chord * 1000,
            dihedral_as_rotation_in_degrees: src?.tip_dihedral ?? 0,
            incidence: src?.tip_incidence ?? tipXsec.twist,
            rotation_point_rel_chord: src?.tip_rotation_point ?? 0.25,
          },
          length: src?.length ?? Math.abs((tipXsec.xyz_le[1] - rootXsec.xyz_le[1]) * 1000),
          sweep: src?.sweep ?? (tipXsec.xyz_le[0] - rootXsec.xyz_le[0]) * 1000,
          number_interpolation_points: src?.number_interpolation_points ?? rootXsec.number_interpolation_points ?? 201,
          tip_type: src?.tip_type || rootXsec.tip_type || undefined,
        };
      });

      const wingConfig = {
        segments,
        nose_pnt: [
          wing.x_secs[0].xyz_le[0] * 1000,
          wing.x_secs[0].xyz_le[1] * 1000,
          wing.x_secs[0].xyz_le[2] * 1000,
        ],
        parameters: "relative",
        symmetric: wing.symmetric,
      };

      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${selectedWing}/from-wingconfig`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(wingConfig),
        },
      );
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Save failed: ${res.status} ${body}`);
      }
      await mutate();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  const handleSave = mode === "wingconfig" ? handleSaveWingConfig : handleSaveAsb;

  return (
    <div className="rounded-[--radius-m] border border-border bg-card p-2.5 px-4">
      {/* Header with mode toggle */}
      <div className="mb-3 flex items-center gap-2">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          segment {selectedXsecIndex} &middot; Properties
        </span>
        <div className="flex-1" />
        <div className="flex overflow-hidden rounded-[--radius-s] border border-border">
          <button
            onClick={() => setMode("wingconfig")}
            className={`px-2.5 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[10px] ${
              mode === "wingconfig"
                ? "bg-primary text-primary-foreground"
                : "bg-card-muted text-muted-foreground hover:text-foreground"
            }`}
          >
            WingConfig
          </button>
          <button
            onClick={() => setMode("asb")}
            className={`px-2.5 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[10px] ${
              mode === "asb"
                ? "bg-primary text-primary-foreground"
                : "bg-card-muted text-muted-foreground hover:text-foreground"
            }`}
          >
            ASB
          </button>
        </div>
      </div>

      {/* Field grid */}
      <div className="flex flex-col gap-3">
        {mode === "wingconfig" && wc ? (
          <>
            {/* Row 1: root_airfoil | tip_airfoil */}
            <div className="flex gap-3">
              <Field
                label="root_airfoil"
                value={wc.root_airfoil}
                type="text"
                isSelect
                onChange={(v) => setWc({ ...wc, root_airfoil: v })}
              />
              <Field
                label="tip_airfoil"
                value={wc.tip_airfoil}
                type="text"
                isSelect
                onChange={(v) => setWc({ ...wc, tip_airfoil: v })}
              />
            </div>
            {/* Row 2: root_chord | tip_chord */}
            <div className="flex gap-3">
              <Field
                label="root_chord"
                value={wc.root_chord}
                suffix="mm"
                onChange={(v) => setWc({ ...wc, root_chord: parseFloat(v) || 0 })}
              />
              <Field
                label="tip_chord"
                value={wc.tip_chord}
                suffix="mm"
                onChange={(v) => setWc({ ...wc, tip_chord: parseFloat(v) || 0 })}
              />
            </div>
            {/* Row 3: length | sweep */}
            <div className="flex gap-3">
              <Field
                label="length"
                value={wc.length}
                suffix="mm"
                onChange={(v) => setWc({ ...wc, length: parseFloat(v) || 0 })}
              />
              <Field
                label="sweep"
                value={wc.sweep}
                suffix="mm"
                onChange={(v) => setWc({ ...wc, sweep: parseFloat(v) || 0 })}
              />
            </div>
            {/* Row 4: dihedral | incidence */}
            <div className="flex gap-3">
              <Field
                label="dihedral"
                value={wc.root_dihedral}
                suffix="°"
                onChange={(v) => setWc({ ...wc, root_dihedral: parseFloat(v) || 0 })}
              />
              <Field
                label="incidence"
                value={wc.root_incidence}
                suffix="°"
                onChange={(v) => setWc({ ...wc, root_incidence: parseFloat(v) || 0 })}
              />
            </div>
            {/* Row 5: rotation_point | interpolation_pts */}
            <div className="flex gap-3">
              <Field
                label="rotation_point"
                value={wc.root_rotation_point}
                onChange={(v) => setWc({ ...wc, root_rotation_point: parseFloat(v) || 0.25 })}
              />
              <Field
                label="interpolation_pts"
                value={wc.number_interpolation_points}
                onChange={(v) => setWc({ ...wc, number_interpolation_points: parseInt(v) || 201 })}
              />
            </div>
          </>
        ) : asb ? (
          <>
            {/* ASB mode: airfoil | chord */}
            <div className="flex gap-3">
              <Field
                label="airfoil"
                value={asb.airfoil}
                type="text"
                onChange={(v) => setAsb({ ...asb, airfoil: v })}
              />
              <Field
                label="chord"
                value={asb.chord}
                suffix="mm"
                onChange={(v) => setAsb({ ...asb, chord: parseFloat(v) || 0 })}
              />
            </div>
            {/* twist | x_sec_type */}
            <div className="flex gap-3">
              <Field
                label="twist"
                value={asb.twist}
                suffix="°"
                onChange={(v) => setAsb({ ...asb, twist: parseFloat(v) || 0 })}
              />
              <Field
                label="x_sec_type"
                value={xsec.x_sec_type ?? "\u2014"}
                readOnly
              />
            </div>
            {/* xyz_le */}
            <div className="flex gap-3">
              {(["x", "y", "z"] as const).map((axis, i) => (
                <Field
                  key={axis}
                  label={`xyz_le.${axis}`}
                  value={asb.xyz_le[i]}
                  suffix="m"
                  onChange={(v) => {
                    const next: [number, number, number] = [...asb.xyz_le];
                    next[i] = parseFloat(v) || 0;
                    setAsb({ ...asb, xyz_le: next });
                  }}
                />
              ))}
            </div>
          </>
        ) : (
          <p className="py-4 text-center text-[12px] text-muted-foreground">
            {mode === "wingconfig"
              ? "Last segment has no WingConfig view (terminal x_sec)"
              : "No data available"}
          </p>
        )}
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
        {error && <p className="text-[12px] text-red-500">{error}</p>}
      </div>
    </div>
  );
}
