"use client";

import { useState } from "react";
import { Check, X } from "lucide-react";
import type { PropertyDefinition, PropertyType } from "@/hooks/useComponentTypes";

interface PropertyEditDialogProps {
  open: boolean;
  initial: PropertyDefinition | null;
  onSave: (prop: PropertyDefinition) => void;
  onCancel: () => void;
}

const SNAKE_CASE = /^[a-z][a-z0-9_]*$/;
const TYPE_OPTIONS: PropertyType[] = ["number", "string", "boolean", "enum"];

interface FormState {
  name: string;
  label: string;
  type: PropertyType;
  unit: string;
  required: boolean;
  description: string;
  min: string;
  max: string;
  optionsCsv: string;
  defaultStr: string;
}

function toForm(prop: PropertyDefinition | null): FormState {
  if (!prop) {
    return {
      name: "", label: "", type: "number", unit: "",
      required: false, description: "", min: "", max: "",
      optionsCsv: "", defaultStr: "",
    };
  }
  return {
    name: prop.name,
    label: prop.label,
    type: prop.type,
    unit: prop.unit ?? "",
    required: !!prop.required,
    description: prop.description ?? "",
    min: prop.min != null ? String(prop.min) : "",
    max: prop.max != null ? String(prop.max) : "",
    optionsCsv: (prop.options ?? []).join(", "),
    defaultStr: prop.default != null ? String(prop.default) : "",
  };
}

type FromFormResult = { ok: true; prop: PropertyDefinition } | { ok: false; error: string };

/** Apply type-specific fields (min/max, options, default) to a partially built prop. */
function applyTypeFields(
  prop: PropertyDefinition,
  f: FormState,
): string | null {
  switch (f.type) {
    case "number":
      if (f.min.trim()) prop.min = Number(f.min);
      if (f.max.trim()) prop.max = Number(f.max);
      if (f.defaultStr.trim()) prop.default = Number(f.defaultStr);
      return null;
    case "enum": {
      const opts = f.optionsCsv.split(",").map((o) => o.trim()).filter(Boolean);
      if (opts.length === 0) return "Enum needs at least one option";
      prop.options = opts;
      if (f.defaultStr.trim()) prop.default = f.defaultStr.trim();
      return null;
    }
    case "boolean":
      if (f.defaultStr.trim()) prop.default = f.defaultStr.trim() === "true";
      return null;
    default:
      if (f.defaultStr.trim()) prop.default = f.defaultStr.trim();
      return null;
  }
}

function fromForm(f: FormState): FromFormResult {
  if (!f.name.trim()) return { ok: false, error: "Name is required" };
  if (!SNAKE_CASE.test(f.name)) {
    return { ok: false, error: "Name must be snake_case (lowercase, digits, underscores)" };
  }
  if (!f.label.trim()) return { ok: false, error: "Label is required" };

  const prop: PropertyDefinition = {
    name: f.name,
    label: f.label,
    type: f.type,
    required: f.required,
  };
  if (f.unit.trim()) prop.unit = f.unit.trim();
  if (f.description.trim()) prop.description = f.description.trim();

  const typeError = applyTypeFields(prop, f);
  if (typeError) return { ok: false, error: typeError };

  return { ok: true, prop };
}

export function PropertyEditDialog({
  open, initial, onSave, onCancel,
}: Readonly<PropertyEditDialogProps>) {
  // The parent is responsible for mounting/unmounting the dialog
  // (`{propDialog.open && <PropertyEditDialog key=... />}`) with a key
  // bound to the edit target — that way initial state seeds correctly
  // from props and we don't need a state-resetting effect (which the
  // react-hooks/set-state-in-effect lint rule forbids).
  const [form, setForm] = useState<FormState>(() => toForm(initial));
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  function update(patch: Partial<FormState>) {
    setForm((prev) => ({ ...prev, ...patch }));
  }

  function handleApply() {
    const result = fromForm(form);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    onSave(result.prop);
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60"
      onClick={onCancel}
    >
      <div
        className="flex w-[440px] flex-col gap-3 rounded-2xl border border-border bg-card p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-foreground">
            {initial ? "Edit Property" : "New Property"}
          </span>
          <span className="flex-1" />
          <button
            onClick={onCancel}
            title="Close"
            className="flex size-7 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
          >
            <X size={12} />
          </button>
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-muted-foreground">Name (snake_case) *</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => update({ name: e.target.value })}
              placeholder="density_kg_m3"
              className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-muted-foreground">Label *</label>
            <input
              type="text"
              value={form.label}
              onChange={(e) => update({ label: e.target.value })}
              placeholder="Dichte"
              className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
            />
          </div>
          <div className="flex gap-2">
            <div className="flex flex-1 flex-col gap-1">
              <label className="text-[11px] text-muted-foreground">Type *</label>
              <select
                value={form.type}
                onChange={(e) => update({ type: e.target.value as PropertyType })}
                className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
              >
                {TYPE_OPTIONS.map((t) => (<option key={t} value={t}>{t}</option>))}
              </select>
            </div>
            <div className="flex flex-1 flex-col gap-1">
              <label className="text-[11px] text-muted-foreground">Unit</label>
              <input
                type="text"
                value={form.unit}
                onChange={(e) => update({ unit: e.target.value })}
                placeholder="kg/m³"
                className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.required}
              onChange={(e) => update({ required: e.target.checked })}
              id="pe-required"
            />
            <label htmlFor="pe-required" className="text-[12px] text-foreground">
              Required
            </label>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] text-muted-foreground">Description</label>
            <input
              type="text"
              value={form.description}
              onChange={(e) => update({ description: e.target.value })}
              className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
            />
          </div>

          {form.type === "number" && (
            // `min-w-0` on flex items + `w-full` on the inputs is required —
            // <input type="number"> has an intrinsic min-width that otherwise
            // keeps the items wider than 1/3 of the row and overflows the
            // modal. Reported visually on Apr-16 for a tube property with a
            // 4-digit default value.
            <div className="flex gap-2">
              <div className="flex min-w-0 flex-1 flex-col gap-1">
                <label className="text-[11px] text-muted-foreground">Min</label>
                <input
                  type="number"
                  value={form.min}
                  onChange={(e) => update({ min: e.target.value })}
                  className="w-full rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
                />
              </div>
              <div className="flex min-w-0 flex-1 flex-col gap-1">
                <label className="text-[11px] text-muted-foreground">Max</label>
                <input
                  type="number"
                  value={form.max}
                  onChange={(e) => update({ max: e.target.value })}
                  className="w-full rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
                />
              </div>
              <div className="flex min-w-0 flex-1 flex-col gap-1">
                <label className="text-[11px] text-muted-foreground">Default</label>
                <input
                  type="number"
                  value={form.defaultStr}
                  onChange={(e) => update({ defaultStr: e.target.value })}
                  className="w-full rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
                />
              </div>
            </div>
          )}

          {form.type === "enum" && (
            <div className="flex flex-col gap-1">
              <label className="text-[11px] text-muted-foreground">Options (comma-separated) *</label>
              <input
                type="text"
                value={form.optionsCsv}
                onChange={(e) => update({ optionsCsv: e.target.value })}
                placeholder="volume, surface"
                className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
              />
            </div>
          )}

          {(form.type === "string" || form.type === "enum" || form.type === "boolean") && (
            <div className="flex flex-col gap-1">
              <label className="text-[11px] text-muted-foreground">Default</label>
              <input
                type="text"
                value={form.defaultStr}
                onChange={(e) => update({ defaultStr: e.target.value })}
                placeholder={form.type === "boolean" ? "true / false" : ""}
                className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
              />
            </div>
          )}
        </div>

        {error && (
          <div className="rounded-xl border border-destructive bg-destructive/10 p-2 text-[11px] text-destructive">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded-full border border-border px-3 py-1.5 text-[12px] text-muted-foreground hover:bg-sidebar-accent"
          >
            Cancel
          </button>
          <button
            onClick={handleApply}
            className="flex items-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-[12px] text-primary-foreground hover:opacity-90"
          >
            <Check size={12} />
            Apply
          </button>
        </div>
      </div>
    </div>
  );
}
