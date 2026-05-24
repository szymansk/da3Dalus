"use client";

import { useId } from "react";

import type { ScaleOption } from "./ImportOpenVspButton";

/**
 * Compact radio group for the optional Quick-Scale during OpenVSP
 * import (gh-695, Variante A). Lives in the AeroplanePickerDialog
 * footer above the Import button.
 *
 * Mutual exclusion is enforced by the radio semantics: only one of
 * the three modes is active at a time. The numeric inputs are only
 * surfaced for their respective mode to keep the footer compact.
 *
 * Bounds match the backend validator (``app.services.openvsp_import_service``):
 * - target_span_m in (0.1, 50) m
 * - scale_factor  in (0.001, 10)
 *
 * The UI uses softer inclusive bounds so the user can type the
 * extremes; the server still rejects out-of-band values with 422.
 */

type Props = {
  value: ScaleOption;
  onChange: (next: ScaleOption) => void;
  disabled?: boolean;
};

function modeOf(opt: ScaleOption): ScaleOption["mode"] {
  return opt.mode;
}

export function ImportScaleInputs({
  value,
  onChange,
  disabled = false,
}: Readonly<Props>) {
  const groupId = useId();
  const noneId = `${groupId}-none`;
  const targetSpanId = `${groupId}-target-span`;
  const scaleFactorId = `${groupId}-scale-factor`;
  const mode = modeOf(value);

  return (
    <fieldset
      className="rounded-lg border border-border bg-input/30 px-3 py-2 text-[12px] text-muted-foreground"
      data-testid="import-scale-inputs"
      disabled={disabled}
    >
      <legend className="px-1 text-[11px] uppercase tracking-wide text-subtle-foreground">
        Optional: scale on import
      </legend>

      <div className="flex flex-col gap-1.5">
        <label
          htmlFor={noneId}
          className="flex items-center gap-2 cursor-pointer"
        >
          <input
            id={noneId}
            type="radio"
            name={`${groupId}-mode`}
            checked={mode === "none"}
            onChange={() => onChange({ mode: "none" })}
            className="accent-primary"
            data-testid="scale-mode-none"
          />
          <span className="text-foreground">Import as-is (default)</span>
        </label>

        <label
          htmlFor={targetSpanId}
          className="flex items-center gap-2 cursor-pointer"
        >
          <input
            id={targetSpanId}
            type="radio"
            name={`${groupId}-mode`}
            checked={mode === "target_span"}
            onChange={() =>
              onChange({
                mode: "target_span",
                target_span_m:
                  value.mode === "target_span" ? value.target_span_m : 1.5,
              })
            }
            className="accent-primary"
            data-testid="scale-mode-target-span"
          />
          <span className="text-foreground">Target wingspan</span>
          <input
            type="number"
            step="0.1"
            min={0.1}
            max={50}
            value={value.mode === "target_span" ? value.target_span_m : ""}
            onChange={(e) => {
              const next = parseFloat(e.target.value);
              if (!Number.isNaN(next)) {
                onChange({ mode: "target_span", target_span_m: next });
              }
            }}
            disabled={mode !== "target_span"}
            placeholder="1.5"
            aria-label="Target wingspan in metres"
            className="w-16 rounded border border-border bg-input px-1.5 py-0.5 text-[12px] text-foreground outline-none disabled:opacity-50"
            data-testid="scale-target-span-input"
          />
          <span className="text-subtle-foreground">m</span>
        </label>

        <label
          htmlFor={scaleFactorId}
          className="flex items-center gap-2 cursor-pointer"
        >
          <input
            id={scaleFactorId}
            type="radio"
            name={`${groupId}-mode`}
            checked={mode === "scale_factor"}
            onChange={() =>
              onChange({
                mode: "scale_factor",
                scale_factor:
                  value.mode === "scale_factor" ? value.scale_factor : 1.0,
              })
            }
            className="accent-primary"
            data-testid="scale-mode-scale-factor"
          />
          <span className="text-foreground">Scale factor</span>
          <input
            type="number"
            step="0.01"
            min={0.001}
            max={10}
            value={value.mode === "scale_factor" ? value.scale_factor : ""}
            onChange={(e) => {
              const next = parseFloat(e.target.value);
              if (!Number.isNaN(next)) {
                onChange({ mode: "scale_factor", scale_factor: next });
              }
            }}
            disabled={mode !== "scale_factor"}
            placeholder="1.0"
            aria-label="Scale factor"
            className="w-16 rounded border border-border bg-input px-1.5 py-0.5 text-[12px] text-foreground outline-none disabled:opacity-50"
            data-testid="scale-factor-input"
          />
          <span className="text-subtle-foreground">×</span>
        </label>
      </div>

      <p className="mt-2 text-[10px] text-subtle-foreground">
        Masses are NOT scaled — adjust manually in mass-properties after import.
      </p>
    </fieldset>
  );
}
