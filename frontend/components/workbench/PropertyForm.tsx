"use client";

import { ChevronDown } from "lucide-react";

interface FieldDef {
  label: string;
  value: string;
  suffix?: string;
  select?: boolean;
}

const FIELD_ROWS: [FieldDef, FieldDef | null][] = [
  [
    { label: "root_airfoil", value: "mh32", select: true },
    { label: "tip_airfoil", value: "mh32", select: true },
  ],
  [
    { label: "length", value: "20.0", suffix: "mm" },
    { label: "sweep", value: "0.0", suffix: "mm" },
  ],
  [
    { label: "dihedral", value: "3.5", suffix: "\u00b0" },
    { label: "incidence", value: "0.0", suffix: "\u00b0" },
  ],
  [{ label: "rotation_point", value: "0.25" }, null],
];

function FieldInput({ field }: { field: FieldDef }) {
  return (
    <div className="flex flex-1 flex-col gap-1">
      <label className="text-[11px] text-muted-foreground">
        {field.label}
      </label>
      <div className="flex items-center gap-2 rounded-[--radius-s] border border-border bg-input px-3 py-2">
        <span className="text-[13px] text-foreground">{field.value}</span>
        <div className="flex-1" />
        {field.select && (
          <ChevronDown size={12} className="text-muted-foreground" />
        )}
        {field.suffix && (
          <span className="text-[11px] text-muted-foreground">
            {field.suffix}
          </span>
        )}
      </div>
    </div>
  );
}

export function PropertyForm() {
  return (
    <div className="rounded-[--radius-m] border border-border bg-card p-2.5 px-4">
      {/* Header */}
      <div className="mb-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          segment 0 &middot; Properties
        </span>
      </div>

      {/* Field grid */}
      <div className="flex flex-col gap-3">
        {FIELD_ROWS.map(([left, right], i) => (
          <div key={i} className="flex gap-3">
            <FieldInput field={left} />
            {right ? (
              <FieldInput field={right} />
            ) : (
              <div className="flex-1" />
            )}
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-2 pt-4">
        <button className="rounded-[--radius-pill] border border-border-strong bg-background px-3.5 py-2 text-[13px] text-foreground hover:bg-sidebar-accent">
          Cancel
        </button>
        <button className="rounded-[--radius-pill] bg-primary px-4 py-2 text-[13px] text-primary-foreground hover:opacity-90">
          Save
        </button>
      </div>
    </div>
  );
}
