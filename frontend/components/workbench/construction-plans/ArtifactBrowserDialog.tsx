"use client";

import { useState, useEffect } from "react";
import { Download, Trash2, X, FolderOpen, File as FileIcon } from "lucide-react";
import { useDialog } from "@/hooks/useDialog";
import {
  usePlanArtifacts,
  useArtifactFiles,
  deleteArtifactFile,
  artifactDownloadUrl,
} from "@/hooks/useConstructionPlans";

interface ArtifactBrowserDialogProps {
  open: boolean;
  planId: number | null;
  planName: string;
  onClose: () => void;
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export function ArtifactBrowserDialog({
  open,
  planId,
  planName,
  onClose,
}: Readonly<ArtifactBrowserDialogProps>) {
  const { dialogRef, handleClose } = useDialog(open, onClose);
  const { executions, isLoading: execLoading, mutate: mutateExecutions } =
    usePlanArtifacts(open ? planId : null);
  const [selectedExecution, setSelectedExecution] = useState<string | null>(null);
  const { files, isLoading: filesLoading, mutate: mutateFiles } =
    useArtifactFiles(open ? planId : null, selectedExecution);

  // Auto-select most recent execution when list loads
  useEffect(() => {
    if (executions.length > 0 && !selectedExecution) {
      setSelectedExecution(executions[0].execution_id);
    }
  }, [executions, selectedExecution]);

  // Reset on close
  useEffect(() => {
    if (!open) {
      setSelectedExecution(null);
    }
  }, [open]);

  async function handleDelete(filename: string) {
    if (!planId || !selectedExecution) return;
    if (!confirm(`Delete "${filename}"?`)) return;
    try {
      await deleteArtifactFile(planId, selectedExecution, filename);
      mutateFiles();
      mutateExecutions();
    } catch (err) {
      alert(`Delete failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  return (
    <dialog
      ref={dialogRef}
      className="m-auto bg-transparent backdrop:bg-black/60"
      onClose={handleClose}
      aria-label={`Artifacts for ${planName}`}
    >
      {open && (
        <div className="flex max-h-[85vh] w-[800px] flex-col rounded-2xl border border-border bg-card shadow-2xl">
          {/* Header */}
          <div className="flex items-center gap-3 border-b border-border px-6 py-4">
            <FolderOpen size={16} className="text-primary" />
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
              Artifacts: {planName}
            </span>
            <span className="flex-1" />
            <button
              onClick={onClose}
              className="flex size-8 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
            >
              <X size={16} />
            </button>
          </div>

          {/* Body */}
          <div className="flex flex-1 overflow-hidden">
            {/* Executions sidebar */}
            <div className="flex w-[240px] flex-col gap-1 overflow-y-auto border-r border-border px-3 py-3">
              <span className="px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] uppercase tracking-wide text-muted-foreground">
                Executions
              </span>
              {execLoading && (
                <p className="px-2 text-[12px] text-muted-foreground">Loading...</p>
              )}
              {!execLoading && executions.length === 0 && (
                <p className="px-2 text-[12px] text-muted-foreground">No executions yet</p>
              )}
              {executions.map((e) => (
                <button
                  key={e.execution_id}
                  onClick={() => setSelectedExecution(e.execution_id)}
                  className={`rounded-lg px-2 py-2 text-left text-[12px] hover:bg-sidebar-accent ${
                    e.execution_id === selectedExecution
                      ? "bg-sidebar-accent text-primary"
                      : "text-foreground"
                  }`}
                >
                  <span className="block font-[family-name:var(--font-jetbrains-mono)]">
                    {e.execution_id}
                  </span>
                  <span className="block text-[10px] text-muted-foreground">
                    {e.file_count} files
                  </span>
                </button>
              ))}
            </div>

            {/* Files list */}
            <div className="flex flex-1 flex-col overflow-y-auto px-6 py-5">
              {!selectedExecution && (
                <p className="text-[13px] text-muted-foreground">
                  Select an execution from the left to view files.
                </p>
              )}
              {selectedExecution && filesLoading && (
                <p className="text-[13px] text-muted-foreground">Loading files...</p>
              )}
              {selectedExecution && !filesLoading && files.length === 0 && (
                <p className="text-[13px] text-muted-foreground">
                  No files in this execution directory.
                </p>
              )}
              {selectedExecution && files.length > 0 && (
                <div className="flex flex-col gap-1">
                  {files.map((f) => (
                    <div
                      key={f.name}
                      className="group flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-sidebar-accent"
                    >
                      <FileIcon size={12} className="text-muted-foreground" />
                      <span className="flex-1 font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground">
                        {f.name}
                      </span>
                      {!f.is_dir && (
                        <span className="text-[11px] text-muted-foreground">
                          {formatBytes(f.size_bytes)}
                        </span>
                      )}
                      {!f.is_dir && planId && (
                        <a
                          href={artifactDownloadUrl(planId, selectedExecution, f.name)}
                          download={f.name}
                          title="Download"
                          className="flex size-6 items-center justify-center rounded-full text-muted-foreground hover:text-primary"
                        >
                          <Download size={12} />
                        </a>
                      )}
                      {!f.is_dir && (
                        <button
                          onClick={() => handleDelete(f.name)}
                          title="Delete"
                          className="flex size-6 items-center justify-center rounded-full text-muted-foreground hover:text-destructive"
                        >
                          <Trash2 size={12} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </dialog>
  );
}
