"use client";

import { useState } from "react";
import { Search, ChevronDown, X, Trash2 } from "lucide-react";
import { useDialog } from "@/hooks/useDialog";
import type { Aeroplane } from "@/hooks/useAeroplanes";
import ImportOpenVspButton, {
  type ImportOpenVspResponse,
  type ScaleOption,
} from "@/components/workbench/ImportOpenVspButton";
import { ImportScaleInputs } from "@/components/workbench/ImportScaleInputs";

interface AeroplanePickerDialogProps {
  open: boolean;
  aeroplanes: Aeroplane[];
  title: string;
  selectedAeroplaneId?: string | null;
  onClose: () => void;
  onSelect: (aeroplaneId: string) => Promise<void> | void;
  onDelete?: (aeroplaneId: string) => Promise<void>;
  onCreate?: (name: string) => Promise<void>;
  /**
   * Optional callback invoked after a successful OpenVSP `.vsp3` upload
   * (gh-695). Receives the full import-response envelope; the host
   * (typically ``AeroplanePickerHost``) is responsible for selecting
   * the new aeroplane, closing the dialog, and surfacing any warnings.
   */
  onImport?: (response: ImportOpenVspResponse) => void;
}

export function AeroplanePickerDialog({
  open,
  aeroplanes,
  title,
  selectedAeroplaneId,
  onClose,
  onSelect,
  onDelete,
  onCreate,
  onImport,
}: Readonly<AeroplanePickerDialogProps>) {
  const { dialogRef, handleClose } = useDialog(open, onClose);
  const [search, setSearch] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<Aeroplane | null>(null);
  // gh-695: Scale-option state co-lives with the picker so the user
  // can pick a mode before triggering the file dialog. Default "none"
  // matches the import-as-is contract.
  const [scaleOption, setScaleOption] = useState<ScaleOption>({ mode: "none" });
  // Optional user-typed name for the imported aeroplane. Empty string
  // means "let the server use the upload filename's stem".
  const [importName, setImportName] = useState("");
  // Local error surface for OpenVSP-specific failures (503 if openvsp
  // isn't installed, 422 if the file is malformed, etc.). Keeps the
  // dialog open so the user can retry without losing context.
  const [importError, setImportError] = useState<string | null>(null);

  const filtered = aeroplanes.filter((a) =>
    a.name.toLowerCase().includes(search.toLowerCase()),
  );

  async function handlePick(id: string) {
    setSubmitting(true);
    try {
      await onSelect(id);
    } catch (err) {
      console.error("handlePick failed:", err);
      alert(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!confirmDelete || !onDelete) return;
    setSubmitting(true);
    try {
      await onDelete(confirmDelete.id);
      setConfirmDelete(null);
    } catch (err) {
      console.error("handleDelete failed:", err);
      alert(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCreate() {
    if (!onCreate) return;
    const name = window.prompt("Aeroplane name?");
    if (!name) return;
    setSubmitting(true);
    try {
      await onCreate(name);
    } catch (err) {
      console.error("handleCreate failed:", err);
      alert(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <dialog
      ref={dialogRef}
      className="m-auto bg-transparent backdrop:bg-black/60"
      onClose={handleClose}
      aria-label={title}
    >
      {open && (
        <div className="flex max-h-[85vh] w-[480px] flex-col rounded-2xl border border-border bg-card shadow-2xl">
          {/* Header */}
          <div className="flex items-center gap-3 border-b border-border px-6 py-4">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
              {title}
            </span>
            <span className="flex-1" />
            <button
              onClick={onClose}
              disabled={submitting}
              className="flex size-8 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent disabled:opacity-50"
            >
              <X size={16} />
            </button>
          </div>

          {/* Body */}
          <div className="flex flex-1 flex-col gap-3 overflow-y-auto px-6 py-5">
            <div className="flex items-center gap-2 rounded-xl border border-border bg-input px-3 py-2">
              <Search className="size-3.5 text-muted-foreground" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search aeroplanes..."
                className="flex-1 bg-transparent text-[13px] text-foreground outline-none placeholder:text-subtle-foreground"
                autoFocus
              />
              <ChevronDown size={12} className="text-muted-foreground" />
            </div>
            <div className="flex flex-col gap-1 max-h-[400px] overflow-y-auto">
              {filtered.length === 0 ? (
                <p className="px-3 py-2 text-[12px] text-muted-foreground">
                  No aeroplanes found
                </p>
              ) : (
                filtered.map((a) => (
                  <div
                    key={a.id}
                    className={`group flex items-center gap-1 rounded-lg hover:bg-sidebar-accent ${a.id === selectedAeroplaneId ? "bg-sidebar-accent/60" : ""}`}
                  >
                    <button
                      type="button"
                      disabled={submitting}
                      onClick={() => handlePick(a.id)}
                      className="flex flex-1 items-center px-3 py-2 text-left text-[13px] text-foreground disabled:opacity-50"
                    >
                      <span className="font-[family-name:var(--font-jetbrains-mono)]">
                        {a.name}
                      </span>
                    </button>
                    {onDelete && (
                      <button
                        type="button"
                        disabled={submitting}
                        onClick={(e) => { e.stopPropagation(); setConfirmDelete(a); }}
                        className="mr-2 flex size-6 items-center justify-center rounded-md text-muted-foreground opacity-0 transition-opacity hover:bg-red-500/20 hover:text-red-400 group-hover:opacity-100 focus-visible:opacity-100 disabled:opacity-50"
                        title={`Delete ${a.name}`}
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
            {confirmDelete && (
              <div className="flex flex-col gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4">
                <p className="text-[13px] text-foreground">
                  Delete <strong>{confirmDelete.name}</strong>? This action cannot be undone.
                </p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={submitting}
                    onClick={() => setConfirmDelete(null)}
                    className="flex-1 rounded-lg border border-border px-3 py-2 text-[13px] text-foreground hover:bg-sidebar-accent disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={submitting}
                    onClick={handleDelete}
                    className="flex-1 rounded-lg bg-red-600 px-3 py-2 text-[13px] text-white hover:bg-red-700 disabled:opacity-50"
                  >
                    Delete
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          {(onCreate || onImport) && (
            <div className="border-t border-border px-6 py-4 space-y-3">
              {onImport && (
                <>
                  <label className="flex flex-col gap-1">
                    <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
                      Aeroplane name (optional)
                    </span>
                    <input
                      type="text"
                      value={importName}
                      onChange={(e) => setImportName(e.target.value)}
                      placeholder="Defaults to the .vsp3 file name"
                      maxLength={200}
                      disabled={submitting}
                      data-testid="aeroplane-picker-import-name"
                      className="rounded-lg border border-border bg-input px-3 py-2 text-[13px] text-foreground outline-none placeholder:text-subtle-foreground focus:border-primary disabled:opacity-50"
                    />
                  </label>
                  <ImportScaleInputs
                    value={scaleOption}
                    onChange={setScaleOption}
                    disabled={submitting}
                  />
                </>
              )}
              {importError && (
                <p
                  role="alert"
                  data-testid="aeroplane-picker-import-error"
                  className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-[12px] text-red-300"
                >
                  {importError}
                </p>
              )}
              <div className="flex gap-2">
                {onCreate && (
                  <button
                    type="button"
                    disabled={submitting}
                    onClick={handleCreate}
                    className="flex-[2] rounded-full bg-primary px-4 py-2.5 text-[13px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
                    data-testid="aeroplane-picker-create-button"
                  >
                    + Create New
                  </button>
                )}
                {onImport && (
                  <ImportOpenVspButton
                    label="Import .vsp3"
                    scaleOption={scaleOption}
                    customName={importName}
                    className="flex-1 rounded-full bg-input/40 text-foreground hover:bg-sidebar-accent"
                    onImported={(response) => {
                      setImportError(null);
                      setImportName("");
                      onImport(response);
                    }}
                    onError={(message) => setImportError(message)}
                  />
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </dialog>
  );
}
