"use client";

import { useRef, useState } from "react";

import ImportProgressBar from "./ImportProgressBar";
import type { ImportOpenVspResponse, ScaleOption } from "@/lib/openvspImport";

/**
 * Frontend upload control for the OpenVSP `.vsp3` importer (gh-646).
 *
 * Single button; opens a hidden `<input type=file>` and POSTs the
 * selected `.vsp3` to ``/api/v2/import/openvsp/stream`` (gh-737). The
 * streaming endpoint yields SSE progress events; during the upload the
 * button is replaced by a real progress bar driven by
 * ``ImportProgressBar``. On the final ``complete`` event the
 * ``onImported`` callback receives the same envelope as the legacy
 * JSON endpoint so the parent can navigate to the new aeroplane and
 * surface warnings via the banner (delivered in gh-648).
 *
 * Optional Quick-Scale (gh-695): when ``scaleOption`` is supplied,
 * the matching query param is appended to the request URL. The
 * backend translates the option to either a target wingspan or a
 * direct multiplier on all length-typed fields. Masses are
 * intentionally NOT scaled (see backend service docstring).
 */
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

export default function ImportOpenVspButton({
  onImported,
  onError,
  className = "",
  label = "Import OpenVSP .vsp3",
  scaleOption,
  customName,
}: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  // ``pendingFile`` holds the user-selected .vsp3 while the streaming
  // import runs. While it's non-null the button is replaced by an
  // ``ImportProgressBar`` driven by the gh-737 SSE endpoint.
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  function handleFile(file: File) {
    if (!file.name.toLowerCase().endsWith(".vsp3")) {
      onError?.("Expected a .vsp3 file.");
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    setPendingFile(file);
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
          if (f) handleFile(f);
        }}
        data-testid="openvsp-file-input"
      />
      {pendingFile ? (
        <div className={`flex-1 ${className}`} data-testid="openvsp-import-progress-wrapper">
          <ImportProgressBar
            file={pendingFile}
            scaleOption={scaleOption}
            customName={customName}
            onComplete={(response) => {
              setPendingFile(null);
              if (inputRef.current) inputRef.current.value = "";
              onImported?.(response);
            }}
            onError={(message) => {
              setPendingFile(null);
              if (inputRef.current) inputRef.current.value = "";
              onError?.(message);
            }}
          />
        </div>
      ) : (
        <button
          type="button"
          className={`rounded border border-neutral-700 px-3 py-1.5 text-sm font-medium text-neutral-200 hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
          onClick={() => inputRef.current?.click()}
          data-testid="openvsp-import-button"
        >
          {label}
        </button>
      )}
    </>
  );
}
