"use client";

import { useId } from "react";

/**
 * Shared labeled number/text input field used inside modal dialogs.
 *
 * Matches the shape of TedField (TedEditDialog) and TurbulatorField
 * (TurbulatorEditDialog) — extracted to eliminate duplication (gh-936).
 */
export function DialogField({
  label,
  value,
  onChange,
  type = "number",
  suffix,
  placeholder,
}: Readonly<{
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: "text" | "number";
  suffix?: string;
  placeholder?: string;
}>) {
  const id = useId();
  return (
    <div className="flex flex-1 flex-col gap-1">
      <label htmlFor={id} className="text-[11px] text-muted-foreground">{label}</label>
      <div className="flex items-center gap-2 rounded-xl border border-border bg-input px-3 py-2">
        <input
          id={id}
          type={type}
          step="any"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full bg-transparent text-[13px] text-foreground outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
        />
        {suffix && (
          <span className="flex-shrink-0 text-[11px] text-muted-foreground">{suffix}</span>
        )}
      </div>
    </div>
  );
}
