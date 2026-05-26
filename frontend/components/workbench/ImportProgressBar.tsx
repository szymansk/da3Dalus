"use client";

import { useEffect, useRef, useState } from "react";

import { API_BASE } from "@/lib/fetcher";
import { parseSseStream } from "@/lib/sseStream";
import type {
  ImportOpenVspResponse,
  ScaleOption,
} from "./ImportOpenVspButton";

/**
 * gh-737: progress bar for the streaming OpenVSP-import endpoint.
 *
 * Driven by ``POST /api/v2/import/openvsp/stream`` which emits SSE
 * progress events (``{step, pct, detail}``) followed by a single
 * ``complete`` event with the same body as the non-stream endpoint
 * (or an ``error`` event with a ``{detail}`` field).
 *
 * The component renders a compact dark-themed bar plus a one-line
 * step label, sized to fit inside the existing aeroplane-picker
 * dialog's import region. Aborts cleanly on unmount.
 */

export type ImportProgressEvent = {
  step: string;
  pct: number;
  detail: string;
};

type StreamEvent =
  | { event: "progress"; data: ImportProgressEvent }
  | { event: "complete"; data: ImportOpenVspResponse }
  | { event: "error"; data: { status: number; detail: string } };

interface Props {
  file: File;
  scaleOption?: ScaleOption;
  customName?: string;
  onComplete: (response: ImportOpenVspResponse) => void;
  onError: (message: string) => void;
}

function buildStreamUrl(scaleOption?: ScaleOption, customName?: string): string {
  const base = `${API_BASE}/api/v2/import/openvsp/stream`;
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

export default function ImportProgressBar({
  file,
  scaleOption,
  customName,
  onComplete,
  onError,
}: Props) {
  const [pct, setPct] = useState(0);
  const [detail, setDetail] = useState("Starting…");
  // Refs over state where possible — the SSE stream callback fires
  // independently of React render cycles and we don't want stale
  // closures.
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);
  useEffect(() => {
    onCompleteRef.current = onComplete;
    onErrorRef.current = onError;
  }, [onComplete, onError]);

  useEffect(() => {
    const controller = new AbortController();

    async function readErrorDetail(res: Response): Promise<string> {
      try {
        const body = await res.json();
        if (typeof body.detail === "string") return body.detail;
      } catch {
        // Non-JSON error response — fall through.
      }
      return `HTTP ${res.status}`;
    }

    function handleEvent(typed: StreamEvent): boolean {
      // Returns ``true`` when the loop should stop (terminal event).
      if (typed.event === "progress") {
        setPct(typed.data.pct);
        setDetail(typed.data.detail);
        return false;
      }
      if (typed.event === "complete") {
        setPct(100);
        setDetail("Done");
        onCompleteRef.current(typed.data);
        return true;
      }
      // error
      const status = typed.data.status ?? 0;
      const prefix = status ? `(${status}) ` : "";
      onErrorRef.current(`${prefix}${typed.data.detail}`);
      return true;
    }

    async function run() {
      try {
        const form = new FormData();
        form.append("file", file);
        const res = await fetch(buildStreamUrl(scaleOption, customName), {
          method: "POST",
          body: form,
          signal: controller.signal,
        });
        if (!res.ok) {
          onErrorRef.current(await readErrorDetail(res));
          return;
        }
        for await (const evt of parseSseStream<unknown>(res)) {
          if (handleEvent(evt as StreamEvent)) return;
        }
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }
        onErrorRef.current(
          err instanceof Error ? err.message : "Unexpected stream error",
        );
      }
    }

    void run();
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run once on mount; props are captured via refs above.

  return (
    <div
      className="space-y-1.5"
      data-testid="openvsp-import-progress"
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className="flex items-baseline justify-between text-xs text-neutral-400">
        <span data-testid="openvsp-import-progress-detail">{detail}</span>
        <span className="font-mono tabular-nums">{pct}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-800">
        <div
          className="h-full bg-orange-500 transition-[width] duration-200 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
