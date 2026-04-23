"use client";

import { useState } from "react";
import type { CreatorParam } from "@/hooks/useCreators";
import { InfoTooltip } from "./InfoTooltip";

interface CreatorParameterFormProps {
  creatorName: string;
  creatorDescription?: string | null;
  params: CreatorParam[];
  values: Record<string, unknown>;
  onChange: (key: string, value: unknown) => void;
  availableShapeKeys?: string[];
}

/** Renders the appropriate input control for a single creator parameter. */
function ParamInput({
  param,
  value,
  onChange,
  availableShapeKeys,
}: {
  param: CreatorParam;
  value: unknown;
  onChange: (key: string, value: unknown) => void;
  availableShapeKeys: string[];
}) {
  const strValue = String(value ?? param.default ?? "");

  if (param.is_shape_ref && availableShapeKeys.length > 0) {
    return (
      <ShapeRefInput
        value={strValue}
        onChange={(v) => onChange(param.name, v)}
        shapeKeys={availableShapeKeys}
        required={param.required}
      />
    );
  }

  if (param.options && param.options.length > 0) {
    return (
      <select
        value={strValue}
        onChange={(e) => onChange(param.name, e.target.value)}
        className="rounded-lg border border-border bg-input px-3 py-1.5 text-[12px] text-foreground outline-none"
      >
        {!param.required && <option value="">—</option>}
        {param.options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
    );
  }

  if (param.type === "bool") {
    return (
      <input
        type="checkbox"
        checked={Boolean(value ?? param.default ?? false)}
        onChange={(e) => onChange(param.name, e.target.checked)}
        className="size-4"
      />
    );
  }

  if (param.type === "int" || param.type === "float") {
    return (
      <input
        type="number"
        value={strValue}
        onChange={(e) => {
          const v = param.type === "int"
            ? Number.parseInt(e.target.value, 10)
            : Number.parseFloat(e.target.value);
          onChange(param.name, Number.isNaN(v) ? null : v);
        }}
        step={param.type === "float" ? "any" : "1"}
        className="rounded-lg border border-border bg-input px-3 py-1.5 text-[12px] text-foreground outline-none"
      />
    );
  }

  return (
    <input
      type="text"
      value={strValue}
      onChange={(e) => onChange(param.name, e.target.value)}
      className="rounded-lg border border-border bg-input px-3 py-1.5 text-[12px] text-foreground outline-none"
    />
  );
}

export function CreatorParameterForm({
  creatorName,
  creatorDescription,
  params,
  values,
  onChange,
  availableShapeKeys = [],
}: Readonly<CreatorParameterFormProps>) {
  return (
    <div className="flex flex-col gap-3">
      {creatorName && (
        <div className="flex items-center gap-2">
          <h3 className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
            {creatorName}
          </h3>
          {creatorDescription && (
            <InfoTooltip text={creatorDescription} size={13} />
          )}
        </div>
      )}
      {params.length === 0 ? (
        <p className="text-[12px] text-muted-foreground">No parameters</p>
      ) : (
        params.map((param) => (
          <label key={param.name} className="flex flex-col gap-1">
            <span className="flex items-center gap-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
              {param.name}
              {param.required && <span className="text-primary"> *</span>}
              <span className="text-[9px] text-subtle-foreground">
                ({param.type})
              </span>
              {param.description && (
                <InfoTooltip text={param.description} size={10} />
              )}
            </span>
            <ParamInput
              param={param}
              value={values[param.name]}
              onChange={onChange}
              availableShapeKeys={availableShapeKeys}
            />
          </label>
        ))
      )}
    </div>
  );
}

/**
 * Searchable combo input for shape-ref parameters.
 * Shows a dropdown of available shape keys with text filtering,
 * but also allows free-text input for kwargs references.
 */
function ShapeRefInput({
  value,
  onChange,
  shapeKeys,
  required,
}: {
  value: string;
  onChange: (v: string) => void;
  shapeKeys: string[];
  required: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const filtered = shapeKeys.filter((k) =>
    k.toLowerCase().includes((search || value).toLowerCase()),
  );

  return (
    <div className="relative">
      <input
        type="text"
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setSearch(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder={required ? "Select shape key..." : "— (optional)"}
        className="w-full rounded-lg border border-border bg-input px-3 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground outline-none"
      />
      {open && filtered.length > 0 && (
        <div className="absolute left-0 top-full z-50 mt-1 max-h-[160px] w-full overflow-y-auto rounded-lg border border-border bg-card shadow-lg">
          {filtered.map((key) => (
            <button
              key={key}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                onChange(key);
                setSearch("");
                setOpen(false);
              }}
              className={`block w-full px-3 py-1.5 text-left font-[family-name:var(--font-jetbrains-mono)] text-[11px] hover:bg-sidebar-accent ${
                key === value ? "bg-sidebar-accent text-primary" : "text-foreground"
              }`}
            >
              {key}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
