"use client";

import type { CreatorParam } from "@/hooks/useCreators";
import { InfoTooltip } from "./InfoTooltip";

interface CreatorParameterFormProps {
  creatorName: string;
  creatorDescription?: string | null;
  params: CreatorParam[];
  values: Record<string, unknown>;
  onChange: (key: string, value: unknown) => void;
}

export function CreatorParameterForm({
  creatorName,
  creatorDescription,
  params,
  values,
  onChange,
}: CreatorParameterFormProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <h3 className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
          {creatorName}
        </h3>
        {creatorDescription && (
          <InfoTooltip text={creatorDescription} size={13} />
        )}
      </div>
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
            {param.type === "bool" ? (
              <input
                type="checkbox"
                checked={Boolean(values[param.name] ?? param.default ?? false)}
                onChange={(e) => onChange(param.name, e.target.checked)}
                className="size-4"
              />
            ) : param.type === "int" || param.type === "float" ? (
              <input
                type="number"
                value={String(values[param.name] ?? param.default ?? "")}
                onChange={(e) => {
                  const v = param.type === "int"
                    ? parseInt(e.target.value, 10)
                    : parseFloat(e.target.value);
                  onChange(param.name, isNaN(v) ? null : v);
                }}
                step={param.type === "float" ? "any" : "1"}
                className="rounded-lg border border-border bg-input px-3 py-1.5 text-[12px] text-foreground outline-none"
              />
            ) : (
              <input
                type="text"
                value={String(values[param.name] ?? param.default ?? "")}
                onChange={(e) => onChange(param.name, e.target.value)}
                className="rounded-lg border border-border bg-input px-3 py-1.5 text-[12px] text-foreground outline-none"
              />
            )}
          </label>
        ))
      )}
    </div>
  );
}
