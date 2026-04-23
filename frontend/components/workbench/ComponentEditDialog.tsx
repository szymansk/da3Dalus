"use client";

import { useId, useState } from "react";
import { ChevronDown, ChevronRight, Loader2, X } from "lucide-react";
import type { Component } from "@/hooks/useComponents";
import { createComponent, updateComponent } from "@/hooks/useComponents";
import {
  useComponentTypes,
  type PropertyDefinition,
} from "@/hooks/useComponentTypes";

interface ComponentEditDialogProps {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  component?: Component | null; // null = create new
}

/** Default value inserted when a type is selected and specs don't already have the key. */
function defaultForProp(prop: PropertyDefinition): unknown {
  if (prop.default != null) return prop.default;
  if (prop.type === "boolean") return false;
  return "";
}

/** Parse a user-entered string back into the property's declared type. */
function parseValue(prop: PropertyDefinition, raw: unknown): unknown {
  if (raw === "" || raw == null) return undefined;
  switch (prop.type) {
    case "number": {
      const n = Number(raw);
      return Number.isFinite(n) ? n : undefined;
    }
    case "boolean":
      if (typeof raw === "boolean") return raw;
      return raw === "true" || raw === true;
    default:
      return String(raw);
  }
}

type ValidationResult = { ok: true } | { ok: false; property: string; message: string };

function fail(prop: PropertyDefinition, message: string): ValidationResult {
  return { ok: false, property: prop.name, message };
}

function validateNumberRange(prop: PropertyDefinition, n: number): ValidationResult | null {
  if (prop.min != null && n < prop.min) {
    return fail(prop, `${prop.label}: expected \u2265 ${prop.min}, got ${n}.`);
  }
  if (prop.max != null && n > prop.max) {
    return fail(prop, `${prop.label}: expected \u2264 ${prop.max}, got ${n}.`);
  }
  return null;
}

function validateProp(prop: PropertyDefinition, raw: unknown): ValidationResult | null {
  const parsed = parseValue(prop, raw);
  if (prop.required && (parsed === undefined || parsed === "")) {
    return fail(prop, `${prop.label} (${prop.name}) is required.`);
  }
  if (parsed === undefined) return null;
  switch (prop.type) {
    case "number":
      return validateNumberRange(prop, parsed as number);
    case "enum":
      if (prop.options && !prop.options.includes(String(parsed))) {
        return fail(prop, `${prop.label}: value '${parsed}' is not in ${JSON.stringify(prop.options)}.`);
      }
      return null;
    default:
      return null;
  }
}

function validate(
  schema: PropertyDefinition[],
  specs: Record<string, unknown>,
): ValidationResult {
  for (const prop of schema) {
    const err = validateProp(prop, specs[prop.name]);
    if (err) return err;
  }
  return { ok: true };
}

export function ComponentEditDialog({
  open, onClose, onSaved, component,
}: Readonly<ComponentEditDialogProps>) {
  const { types } = useComponentTypes();
  const isEdit = !!component;

  // All state is seeded once on mount — parent is responsible for mounting/
  // unmounting us conditionally so that reopening seeds from fresh props.
  const [name, setName] = useState(component?.name ?? "");
  const [componentType, setComponentType] = useState(
    component?.component_type ?? "generic",
  );
  const [manufacturer, setManufacturer] = useState(component?.manufacturer ?? "");
  const [description, setDescription] = useState(component?.description ?? "");
  const [massG, setMassG] = useState(
    component?.mass_g != null ? String(component.mass_g) : "",
  );
  const [specs, setSpecs] = useState<Record<string, unknown>>(
    { ...(component?.specs ?? {}) },
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showUnknown, setShowUnknown] = useState(false);

  if (!open) return null;

  const currentType = types.find((t) => t.name === componentType);
  const schema: PropertyDefinition[] = currentType?.schema ?? [];
  const schemaKeys = new Set(schema.map((p) => p.name));
  const unknownKeys = Object.keys(specs).filter((k) => !schemaKeys.has(k));

  function handleTypeChange(newType: string) {
    setComponentType(newType);
    // Defaults for keys that are new in the target schema get seeded from
    // the property's `default`; keys that were already set stay; keys that
    // aren't in the new schema remain in `specs` (tolerant mode) but aren't
    // rendered.
    const newSchema =
      types.find((t) => t.name === newType)?.schema ?? [];
    setSpecs((prev) => {
      const next = { ...prev };
      for (const prop of newSchema) {
        if (!(prop.name in next)) next[prop.name] = defaultForProp(prop);
      }
      return next;
    });
  }

  function setSpec(propName: string, value: unknown) {
    setSpecs((prev) => ({ ...prev, [propName]: value }));
  }

  /** Build the final specs object: parse known keys, keep unknown keys raw. */
  function buildOutSpecs(): Record<string, unknown> {
    const out: Record<string, unknown> = {};
    for (const prop of schema) {
      const parsed = parseValue(prop, specs[prop.name]);
      if (parsed !== undefined) out[prop.name] = parsed;
    }
    for (const key of unknownKeys) {
      out[key] = specs[key];
    }
    return out;
  }

  async function handleSave() {
    if (!name.trim()) { setError("Name is required"); return; }
    const result = validate(schema, specs);
    if (!result.ok) {
      setError(result.message);
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const data = {
        name: name.trim(),
        component_type: componentType,
        manufacturer: manufacturer.trim() || null,
        description: description.trim() || null,
        mass_g: massG ? Number.parseFloat(massG) : null,
        bbox_x_mm: null,
        bbox_y_mm: null,
        bbox_z_mm: null,
        model_ref: null,
        specs: buildOutSpecs(),
      };
      if (isEdit && component) {
        await updateComponent(component.id, data as unknown as Component);
      } else {
        await createComponent(data as unknown as Component);
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  let submitLabel = "Create";
  if (saving) submitLabel = "Saving\u2026";
  else if (isEdit) submitLabel = "Update";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      role="dialog"
      aria-modal="true"
      aria-label={isEdit ? "Edit Component" : "New Component"}
      onClick={onClose}
      onKeyDown={(e) => { if (e.key === "Escape") onClose(); }}
    >
      <div
        className="flex max-h-[85vh] w-[520px] flex-col gap-4 rounded-2xl border border-border bg-card p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
            {isEdit ? "Edit Component" : "New Component"}
          </span>
          <span className="flex-1" />
          <button
            onClick={onClose}
            className="flex size-8 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex flex-col gap-3 overflow-y-auto">
          <div className="flex flex-col gap-1">
            <label htmlFor="ce-name" className="text-[11px] text-muted-foreground">Name *</label>
            <input
              id="ce-name"
              type="text" value={name} onChange={(e) => setName(e.target.value)}
              className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
            />
          </div>
          {/*
           * `min-w-0` on the flex items + `w-full` on the controls — same
           * pattern as the PropertyEditDialog Min/Max/Default fix. Without
           * it, a <select> element sizes to fit its longest option, which
           * can push the row wider than the modal when a user-added type
           * has a very long name. Reported 2026-04-16 for a garbage type
           * name of ~60 characters.
           */}
          <div className="flex gap-3">
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <label htmlFor="ce-type" className="text-[11px] text-muted-foreground">Type</label>
              <select
                id="ce-type"
                value={componentType}
                onChange={(e) => handleTypeChange(e.target.value)}
                className="w-full truncate rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
              >
                {types.map((t) => (
                  <option key={t.id} value={t.name}>{t.label}</option>
                ))}
              </select>
            </div>
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <label htmlFor="ce-mass" className="text-[11px] text-muted-foreground">Mass (g)</label>
              <input
                id="ce-mass"
                type="number" value={massG} onChange={(e) => setMassG(e.target.value)}
                className="w-full rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
              />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="ce-manufacturer" className="text-[11px] text-muted-foreground">Manufacturer</label>
            <input
              id="ce-manufacturer"
              type="text" value={manufacturer}
              onChange={(e) => setManufacturer(e.target.value)}
              className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="ce-description" className="text-[11px] text-muted-foreground">Description</label>
            <textarea
              id="ce-description"
              value={description} onChange={(e) => setDescription(e.target.value)} rows={2}
              className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground resize-none"
            />
          </div>

          {schema.length > 0 && (
            <>
              <div className="mt-1 flex items-center gap-2">
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground uppercase tracking-wide">
                  {currentType?.label} properties
                </span>
              </div>
              {schema.map((prop) => (
                <SpecField
                  key={prop.name}
                  prop={prop}
                  value={specs[prop.name]}
                  onChange={(v) => setSpec(prop.name, v)}
                />
              ))}
            </>
          )}

          {unknownKeys.length > 0 && (
            <div className="mt-2 rounded-xl border border-border bg-card-muted px-3 py-2">
              <button
                onClick={() => setShowUnknown((v) => !v)}
                className="flex w-full items-center gap-1 text-[11px] text-muted-foreground"
              >
                {showUnknown ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                Unknown properties ({unknownKeys.length})
              </button>
              {showUnknown && (
                <ul className="mt-2 flex flex-col gap-1 pl-4">
                  {unknownKeys.map((k) => (
                    <li key={k} className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-subtle-foreground">
                      {k}: {typeof specs[k] === "object" ? JSON.stringify(specs[k]) : String(specs[k])}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        {error && (
          <div className="rounded-xl border border-destructive bg-destructive/10 p-3 text-[12px] text-destructive">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose} disabled={saving}
            className="rounded-full border border-border px-4 py-2 text-[13px] text-muted-foreground hover:bg-sidebar-accent"
          >
            Cancel
          </button>
          <button
            onClick={handleSave} disabled={saving}
            className="flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-[13px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {saving && <Loader2 size={14} className="animate-spin" />}
            {submitLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// SpecField — renders a single property-schema entry as the right input type.
// --------------------------------------------------------------------------- //

interface SpecFieldProps {
  prop: PropertyDefinition;
  value: unknown;
  onChange: (v: unknown) => void;
}

function SpecField({ prop, value, onChange }: Readonly<SpecFieldProps>) {
  const fieldId = useId();
  const labelText = `${prop.label}${prop.required ? " *" : ""}${prop.unit ? ` (${prop.unit})` : ""}`;

  switch (prop.type) {
    case "boolean":
      return (
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            data-spec={prop.name}
            checked={!!value}
            onChange={(e) => onChange(e.target.checked)}
            id={fieldId}
          />
          <label htmlFor={fieldId} className="text-[12px] text-foreground">
            {labelText}
          </label>
        </div>
      );

    case "enum":
      return (
        <div className="flex flex-col gap-1">
          <label htmlFor={fieldId} className="text-[11px] text-muted-foreground">{labelText}</label>
          <select
            id={fieldId}
            data-spec={prop.name}
            value={value == null ? "" : String(value)}
            onChange={(e) => onChange(e.target.value)}
            className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
          >
            <option value=""></option>
            {(prop.options ?? []).map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
        </div>
      );

    default:
      // number or string
      return (
        <div className="flex flex-col gap-1">
          <label htmlFor={fieldId} className="text-[11px] text-muted-foreground">{labelText}</label>
          <input
            id={fieldId}
            data-spec={prop.name}
            type={prop.type === "number" ? "number" : "text"}
            value={value == null ? "" : String(value)}
            onChange={(e) => onChange(e.target.value)}
            min={prop.min ?? undefined}
            max={prop.max ?? undefined}
            className="rounded-xl border border-border bg-input px-3 py-2 text-[13px] text-foreground"
          />
          {prop.description && (
            <span className="text-[10px] text-subtle-foreground">{prop.description}</span>
          )}
        </div>
      );
  }
}
