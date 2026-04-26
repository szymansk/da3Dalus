"use client";

import { useState } from "react";
import { Download, Trash2, X, FolderOpen, ChevronRight, File as FileIcon } from "lucide-react";
import { useDialog } from "@/hooks/useDialog";
import {
  usePlanArtifacts,
  useArtifactFiles,
  deleteArtifactFile,
  deleteExecution,
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
  const { executions, error: execError, isLoading: execLoading, mutate: mutateExecutions } =
    usePlanArtifacts(open ? planId : null);
  const [selectedOverride, setSelectedOverride] = useState<string | null>(null);
  const [currentPath, setCurrentPath] = useState("");
  const [prevOpen, setPrevOpen] = useState(open);

  // Reset state when the dialog closes. Render-time setState is the React 19
  // recommended pattern for "adjust state when a prop changes" — see
  // react-hooks/set-state-in-effect.
  if (open !== prevOpen) {
    setPrevOpen(open);
    if (!open) {
      setSelectedOverride(null);
      setCurrentPath("");
    }
  }

  // Effective selection: explicit override wins, otherwise auto-pick the most
  // recent execution. Deriving this avoids a useEffect+setState cycle.
  const selectedExecution = selectedOverride ?? executions[0]?.execution_id ?? null;

  const { files, error: filesError, isLoading: filesLoading, mutate: mutateFiles } =
    useArtifactFiles(open ? planId : null, selectedExecution, currentPath);

  async function handleDeleteExecution(executionId: string) {
    if (!planId) return;
    if (!confirm(`Delete execution ${executionId} and all its files? This cannot be undone.`)) return;
    try {
      await deleteExecution(planId, executionId);
      mutateExecutions();
      if (selectedExecution === executionId) {
        setSelectedOverride(null);
        setCurrentPath("");
      }
    } catch (err) {
      alert(`Delete failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

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
              {execError && (
                <div className="px-2 py-1">
                  <p className="text-[12px] text-destructive">Failed to load executions</p>
                  <button onClick={() => mutateExecutions()} className="text-[11px] text-primary hover:underline">Retry</button>
                </div>
              )}
              {!execLoading && !execError && executions.length === 0 && (
                <p className="px-2 text-[12px] text-muted-foreground">No executions yet</p>
              )}
              {executions.map((e) => (
                <div
                  key={e.execution_id}
                  className={`group/exec flex items-center rounded-lg px-2 py-2 text-[12px] hover:bg-sidebar-accent ${
                    e.execution_id === selectedExecution
                      ? "bg-sidebar-accent text-primary"
                      : "text-foreground"
                  }`}
                >
                  <button
                    onClick={() => { setSelectedOverride(e.execution_id); setCurrentPath(""); }}
                    className="flex-1 text-left"
                  >
                    <span className="block font-[family-name:var(--font-jetbrains-mono)]">
                      {e.execution_id}
                    </span>
                    <span className="block text-[10px] text-muted-foreground">
                      {e.file_count} files
                    </span>
                  </button>
                  <button
                    onClick={(ev) => { ev.stopPropagation(); handleDeleteExecution(e.execution_id); }}
                    title="Delete execution"
                    className="hidden shrink-0 size-5 items-center justify-center rounded-lg text-destructive group-hover/exec:flex"
                  >
                    <Trash2 size={10} />
                  </button>
                </div>
              ))}
            </div>

            {/* Files list */}
            <div className="flex flex-1 flex-col overflow-y-auto px-6 py-5">
              {/* Breadcrumb navigation */}
              {selectedExecution && currentPath && (
                <div className="mb-2 flex items-center gap-1 text-[12px]">
                  <button
                    onClick={() => setCurrentPath("")}
                    className="text-primary hover:underline"
                  >
                    /
                  </button>
                  {currentPath.split("/").map((segment, i, arr) => (
                    <span key={i} className="flex items-center gap-1">
                      <ChevronRight size={10} className="text-muted-foreground" />
                      <button
                        onClick={() => setCurrentPath(arr.slice(0, i + 1).join("/"))}
                        className={i === arr.length - 1 ? "text-foreground" : "text-primary hover:underline"}
                      >
                        {segment}
                      </button>
                    </span>
                  ))}
                </div>
              )}

              {!selectedExecution && (
                <p className="text-[13px] text-muted-foreground">
                  Select an execution from the left to view files.
                </p>
              )}
              {selectedExecution && filesError && (
                <div>
                  <p className="text-[13px] text-destructive">Failed to load files</p>
                  <button onClick={() => mutateFiles()} className="text-[12px] text-primary hover:underline">Retry</button>
                </div>
              )}
              {selectedExecution && !filesError && filesLoading && (
                <p className="text-[13px] text-muted-foreground">Loading files...</p>
              )}
              {selectedExecution && !filesError && !filesLoading && files.length === 0 && (
                <p className="text-[13px] text-muted-foreground">
                  {currentPath ? "Empty directory." : "No files in this execution directory."}
                </p>
              )}
              {selectedExecution && files.length > 0 && (
                <div className="flex flex-col gap-1">
                  {files.map((f) => (
                    <div
                      key={f.name}
                      className={`group flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-sidebar-accent ${f.is_dir ? "cursor-pointer" : ""}`}
                      onClick={f.is_dir ? () => setCurrentPath(currentPath ? `${currentPath}/${f.name}` : f.name) : undefined}
                    >
                      {f.is_dir ? (
                        <FolderOpen size={12} className="text-primary" />
                      ) : (
                        <FileIcon size={12} className="text-muted-foreground" />
                      )}
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
                          href={artifactDownloadUrl(planId, selectedExecution, currentPath ? `${currentPath}/${f.name}` : f.name)}
                          download={f.name}
                          title="Download"
                          className="flex size-6 items-center justify-center rounded-full text-muted-foreground hover:text-primary"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Download size={12} />
                        </a>
                      )}
                      {!f.is_dir && (
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDelete(f.name); }}
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
