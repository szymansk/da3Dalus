"use client";

import { X } from "lucide-react";
import { useDialog } from "@/hooks/useDialog";
import { CadViewer } from "@/components/workbench/CadViewer";
import type { ExecutionResult } from "@/hooks/useConstructionPlans";

interface ExecutionResultDialogProps {
  open: boolean;
  title: string;
  result: ExecutionResult | null;
  onClose: () => void;
}

export function ExecutionResultDialog({
  open,
  title,
  result,
  onClose,
}: Readonly<ExecutionResultDialogProps>) {
  const { dialogRef, handleClose } = useDialog(open, onClose);

  // Build parts array for CadViewer from tessellation. The backend can return
  // a single tessellation object or an array; normalize either to an array.
  const parts = (() => {
    if (!result?.tessellation) return [];
    const t = result.tessellation as Record<string, unknown> | Record<string, unknown>[];
    return Array.isArray(t) ? t : [t];
  })();

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
            {result && result.status === "success" && (
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
                {result.shape_keys?.length ?? 0} shapes · {result.duration_ms} ms
              </span>
            )}
            <span className="flex-1" />
            <button
              onClick={onClose}
              className="flex size-8 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
            >
              <X size={16} />
            </button>
          </div>

          {/* Body */}
          <div className="flex h-[600px] flex-1 flex-col overflow-hidden">
            {!result && (
              <div className="flex flex-1 items-center justify-center">
                <p className="text-[13px] text-muted-foreground">Executing...</p>
              </div>
            )}
            {result && result.status === "error" && (
              <div className="flex flex-1 items-center justify-center px-6">
                <div className="rounded-xl border border-destructive bg-destructive/10 p-4 text-[13px] text-destructive">
                  <p className="font-medium">Execution failed</p>
                  <p className="mt-1 text-[12px] opacity-80">{result.error ?? "Unknown error"}</p>
                </div>
              </div>
            )}
            {result && result.status === "success" && parts.length > 0 && (
              <CadViewer parts={parts} />
            )}
            {result && result.status === "success" && parts.length === 0 && (
              <div className="flex flex-1 items-center justify-center">
                <p className="text-[13px] text-muted-foreground">
                  No tessellation data to display
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </dialog>
  );
}
