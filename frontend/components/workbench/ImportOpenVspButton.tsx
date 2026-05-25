"use client";

import { useRef, useState } from "react";

import { API_BASE } from "@/lib/fetcher";

/**
 * Frontend upload control for the OpenVSP `.vsp3` importer (gh-646).
 *
 * Single button; opens a hidden `<input type=file>` and POSTs the
 * selected `.vsp3` to `/api/v2/import/openvsp`. On success the
 * `onImported` callback receives the response envelope so the parent
 * can navigate to the new aeroplane and surface warnings via the
 * banner (delivered in gh-648).
 *
 * Optional Quick-Scale (gh-695): when ``scaleOption`` is supplied,
 * the matching query param is appended to the request URL. The
 * backend translates the option to either a target wingspan or a
 * direct multiplier on all length-typed fields. Masses are
 * intentionally NOT scaled (see backend service docstring).
 */
export type ImportOpenVspWarning = {
  component_type: string;
  component_name: string;
  reason: string;
  severity: "info" | "warning" | "error";
};

export type ImportOpenVspResponse = {
  aeroplane_uuid: string;
  aeroplane_name: string;
  n_wings: number;
  n_fuselages: number;
  n_weight_items: number;
  warnings: ImportOpenVspWarning[];
  lossy_components: string[];
};

/**
 * Optional scaling instruction for the import request.
 *
 * - ``none``        — import as-is, no rescale.
 * - ``target_span`` — rescale to the requested wingspan in metres.
 * - ``scale_factor``— multiply all length-typed fields by the factor.
 *
 * Both ``target_span_m`` and ``scale_factor`` are validated server-side
 * (out-of-range → 422). The UI should also enforce reasonable bounds
 * to prevent obvious mistakes.
 */
export type ScaleOption =
  | { mode: "none" }
  | { mode: "target_span"; target_span_m: number }
  | { mode: "scale_factor"; scale_factor: number };

type Props = {
  onImported?: (response: ImportOpenVspResponse) => void;
  onError?: (message: string) => void;
  className?: string;
  label?: string;
  scaleOption?: ScaleOption;
  /**
   * Optional user-supplied aeroplane name forwarded to the backend as
   * ``?name=<value>``. Empty / whitespace-only values are dropped so
   * the server falls back to the uploaded filename's stem (the
   * desired default).
   */
  customName?: string;
};

function buildImportUrl(scaleOption?: ScaleOption, customName?: string): string {
  const base = `${API_BASE}/api/v2/import/openvsp`;
  const params = new URLSearchParams();
  if (scaleOption?.mode === "target_span") {
    params.set("target_span_m", String(scaleOption.target_span_m));
  } else if (scaleOption?.mode === "scale_factor") {
    params.set("scale_factor", String(scaleOption.scale_factor));
  }
  const trimmedName = customName?.trim() ?? "";
  if (trimmedName) {
    params.set("name", trimmedName);
  }
  const qs = params.toString();
  return qs ? `${base}?${qs}` : base;
}

export default function ImportOpenVspButton({
  onImported,
  onError,
  className = "",
  label = "Import OpenVSP .vsp3",
  scaleOption,
  customName,
}: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [uploading, setUploading] = useState(false);

  async function handleFile(file: File) {
    if (!file.name.toLowerCase().endsWith(".vsp3")) {
      onError?.("Expected a .vsp3 file.");
      return;
    }
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(buildImportUrl(scaleOption, customName), {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try {
          const body = await res.json();
          detail = typeof body.detail === "string" ? body.detail : detail;
        } catch {
          // Ignore JSON parse errors — keep the HTTP-status default.
        }
        onError?.(detail);
        return;
      }
      const body = (await res.json()) as ImportOpenVspResponse;
      onImported?.(body);
    } catch (err) {
      onError?.(
        err instanceof Error ? err.message : "Unexpected error during import",
      );
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept=".vsp3"
        style={{ display: "none" }}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void handleFile(f);
        }}
        data-testid="openvsp-file-input"
      />
      <button
        type="button"
        className={`rounded border border-neutral-700 px-3 py-1.5 text-sm font-medium text-neutral-200 hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
        disabled={uploading}
        onClick={() => inputRef.current?.click()}
        data-testid="openvsp-import-button"
      >
        {uploading ? "Importing…" : label}
      </button>
    </>
  );
}
