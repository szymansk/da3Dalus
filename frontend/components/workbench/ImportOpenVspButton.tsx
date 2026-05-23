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

type Props = {
  onImported?: (response: ImportOpenVspResponse) => void;
  onError?: (message: string) => void;
  className?: string;
  label?: string;
};

export default function ImportOpenVspButton({
  onImported,
  onError,
  className = "",
  label = "Import OpenVSP .vsp3",
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
      const res = await fetch(`${API_BASE}/api/v2/import/openvsp`, {
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
