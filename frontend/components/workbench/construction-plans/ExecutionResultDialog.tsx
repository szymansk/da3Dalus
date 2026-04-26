"use client";

import { useEffect, useState, useRef } from "react";
import { X } from "lucide-react";
import { useDialog } from "@/hooks/useDialog";
import { CadViewer } from "@/components/workbench/CadViewer";
import {
  artifactDownloadUrl,
  executionZipUrl,
  useArtifactFiles,
} from "@/hooks/useConstructionPlans";
import type { ExecutionResult } from "@/hooks/useConstructionPlans";

interface ExecutionResultDialogProps {
  open: boolean;
  title: string;
  /** Pre-computed result (non-streaming mode). */
  result?: ExecutionResult | null;
  /** SSE URL for streaming mode. When set, streams shapes incrementally. */
  streamUrl?: string | null;
  /** Plan/template id for the artifact endpoints. */
  planId?: number | null;
  /** Execution id (resolved from result or streamed 'complete' event). */
  executionId?: string | null;
  onClose: () => void;
}

export function ExecutionResultDialog({
  open,
  title,
  result: preResult,
  streamUrl,
  planId,
  executionId,
  onClose,
}: Readonly<ExecutionResultDialogProps>) {
  const { dialogRef, handleClose } = useDialog(open, onClose);
  const [streamedParts, setStreamedParts] = useState<Record<string, unknown>[]>([]);
  const [status, setStatus] = useState<"executing" | "success" | "error">("executing");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string>("");
  const [streamedExecutionId, setStreamedExecutionId] = useState<string | null>(
    null,
  );
  const eventSourceRef = useRef<EventSource | null>(null);

  // SSE streaming
  useEffect(() => {
    if (!open || !streamUrl) return;
    setStreamedParts([]);
    setStatus("executing");
    setError(null);
    setInfo("");
    setStreamedExecutionId(null);

    const es = new EventSource(streamUrl);
    eventSourceRef.current = es;

    let retryCount = 0;

    es.addEventListener("shape", (e) => {
      retryCount = 0; // reset on successful event
      try {
        const data = JSON.parse(e.data);
        if (data.tessellation) {
          setStreamedParts((prev) => [...prev, data.tessellation]);
          setInfo(data.name ?? "");
        }
      } catch (err) {
        console.warn("[ExecutionStream] Malformed shape event:", err);
      }
    });

    es.addEventListener("complete", (e) => {
      try {
        const data = JSON.parse(e.data);
        setStatus("success");
        setInfo(`${data.shape_keys?.length ?? 0} shapes · ${data.duration_ms} ms`);
        if (data.execution_id) setStreamedExecutionId(data.execution_id);
        if (data.tessellation) {
          setStreamedParts([data.tessellation]);
        }
      } catch (err) {
        console.error("[ExecutionStream] Failed to parse complete event:", err);
        setStatus("success");
        setInfo("Completed (response parsing failed)");
      }
      es.close();
    });

    es.addEventListener("error", (e) => {
      if (es.readyState === EventSource.CLOSED) return;
      try {
        const data = JSON.parse((e as MessageEvent).data ?? "{}");
        setError(data.error ?? "Execution failed");
        setStatus("error");
        es.close();
      } catch {
        // Native EventSource error (network/connection issue)
        retryCount++;
        if (retryCount > 3) {
          setError("Cannot connect to execution server. Please check that the backend is running.");
          setStatus("error");
          es.close();
        }
      }
    });

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [open, streamUrl]);

  // Non-streaming mode: build parts from pre-computed result
  const nonStreamParts = (() => {
    if (!preResult?.tessellation) return [];
    const t = preResult.tessellation as Record<string, unknown> | Record<string, unknown>[];
    return Array.isArray(t) ? t : [t];
  })();

  const isStreaming = !!streamUrl;
  const parts = isStreaming ? streamedParts : nonStreamParts;
  const effectiveStatus = isStreaming ? status : (preResult ? preResult.status : "executing");
  const effectiveError = isStreaming ? error : preResult?.error;
  const effectiveInfo = isStreaming
    ? info
    : (preResult?.status === "success" ? `${preResult.shape_keys?.length ?? 0} shapes · ${preResult.duration_ms} ms` : "");
  const effectiveExecutionId = isStreaming
    ? streamedExecutionId
    : (preResult?.execution_id ?? executionId ?? null);

  return (
    <dialog
      ref={dialogRef}
      className="m-auto bg-transparent backdrop:bg-black/60"
      onClose={handleClose}
      aria-label={title}
    >
      {open && (
        <div className="flex max-h-[90vh] w-[1000px] flex-col rounded-2xl border border-border bg-card shadow-2xl">
          {/* Header */}
          <div className="flex items-center gap-3 border-b border-border px-6 py-4">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
              {title}
            </span>
            {effectiveStatus === "executing" && (
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-primary animate-pulse">
                {info || "Executing..."}
              </span>
            )}
            {effectiveStatus === "success" && effectiveInfo && (
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
                {effectiveInfo}
              </span>
            )}
            <span className="flex-1" />
            <button
              onClick={() => {
                eventSourceRef.current?.close();
                onClose();
              }}
              className="flex size-8 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
            >
              <X size={16} />
            </button>
          </div>

          {/* Body */}
          <div className="flex h-[600px] flex-1 flex-col overflow-hidden">
            {effectiveStatus === "error" && (
              <div className="flex flex-1 items-center justify-center px-6">
                <div className="rounded-xl border border-destructive bg-destructive/10 p-4 text-[13px] text-destructive">
                  <p className="font-medium">Execution failed</p>
                  <p className="mt-1 text-[12px] opacity-80">{effectiveError ?? "Unknown error"}</p>
                </div>
              </div>
            )}
            {effectiveStatus !== "error" && parts.length > 0 && (
              <CadViewer parts={parts} />
            )}
            {effectiveStatus === "executing" && parts.length === 0 && (
              <div className="flex flex-1 items-center justify-center">
                <p className="text-[13px] text-muted-foreground animate-pulse">
                  Waiting for shapes...
                </p>
              </div>
            )}
            {effectiveStatus === "success" && parts.length === 0 && (
              <div className="flex flex-1 items-center justify-center">
                <p className="text-[13px] text-muted-foreground">
                  No tessellation data to display
                </p>
              </div>
            )}
          </div>

          {effectiveStatus === "success" && (
            <GeneratedFilesSection
              planId={planId ?? null}
              executionId={effectiveExecutionId}
            />
          )}
        </div>
      )}
    </dialog>
  );
}

function GeneratedFilesSection({
  planId,
  executionId,
}: Readonly<{ planId: number | null; executionId: string | null }>) {
  const { files, isLoading } = useArtifactFiles(planId, executionId);

  if (planId == null || executionId == null) return null;

  const visibleFiles = files.filter((f) => !f.is_dir);

  return (
    <div className="border-t border-border px-6 py-4">
      <div className="mb-2 flex items-center gap-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          Generated files
        </span>
        <span className="flex-1" />
        {visibleFiles.length > 0 && (
          <a
            href={executionZipUrl(planId, executionId)}
            className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-primary hover:underline"
            download
          >
            Download zip
          </a>
        )}
      </div>
      {isLoading ? (
        <p className="text-[12px] text-muted-foreground">Loading files...</p>
      ) : visibleFiles.length === 0 ? (
        <p className="text-[12px] text-muted-foreground">No files generated.</p>
      ) : (
        <ul className="flex max-h-32 flex-col gap-1 overflow-y-auto">
          {visibleFiles.map((f) => (
            <li key={f.name} className="flex items-center gap-2 text-[12px]">
              <a
                href={artifactDownloadUrl(planId, executionId, f.name)}
                className="text-primary hover:underline"
                download
              >
                {f.name}
              </a>
              <span className="text-muted-foreground">
                ({Math.max(1, Math.round(f.size_bytes / 1024))} KB)
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
