"use client";

import { useState } from "react";
import { ArrowDown, ArrowUp, X } from "lucide-react";
import { useDialog } from "@/hooks/useDialog";
import { CreatorParameterForm } from "@/components/workbench/CreatorParameterForm";
import type { CreatorInfo } from "@/hooks/useCreators";
import type { MockCreatorNode } from "./types";

interface EditParamsModalProps {
  open: boolean;
  creator: MockCreatorNode | null;
  creatorInfo: CreatorInfo | null;
  onClose: () => void;
}

export function EditParamsModal({
  open,
  creator,
  creatorInfo,
  onClose,
}: Readonly<EditParamsModalProps>) {
  const { dialogRef, handleClose } = useDialog(open, onClose);
  const [values, setValues] = useState<Record<string, unknown>>({});

  // Reset values when creator changes
  const currentCreatorId = creator?.creatorId;
  const [lastCreatorId, setLastCreatorId] = useState<string | null>(null);
  if (currentCreatorId && currentCreatorId !== lastCreatorId) {
    setLastCreatorId(currentCreatorId);
    setValues(creator?.mockParams ?? {});
  }

  return (
    <dialog
      ref={dialogRef}
      className="m-auto bg-transparent backdrop:bg-black/60"
      onClose={handleClose}
      aria-label={creator ? `Edit ${creator.creatorId}` : "Edit Parameters"}
    >
      {open && creator && (
        <div className="flex max-h-[85vh] w-[520px] flex-col rounded-2xl border border-border bg-card shadow-2xl">
          {/* Header */}
          <div className="flex items-center gap-3 border-b border-border px-6 py-4">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
              Edit {creator.creatorId}
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
          <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-6 py-5">
            {creator.shapes.length > 0 && (
              <div className="flex flex-col gap-1 rounded-xl border border-border bg-card-muted/30 p-3">
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
                  Shapes
                </span>
                {creator.shapes.map((s) => (
                  <div
                    key={`${s.direction}-${s.name}`}
                    className="flex items-center gap-2 text-[12px] text-muted-foreground"
                  >
                    {s.direction === "input" ? (
                      <ArrowDown size={10} className="text-blue-400" />
                    ) : (
                      <ArrowUp size={10} className="text-emerald-400" />
                    )}
                    <span className="font-[family-name:var(--font-jetbrains-mono)]">{s.name}</span>
                    <span className="text-[10px] text-subtle-foreground">({s.direction})</span>
                  </div>
                ))}
              </div>
            )}

            {creatorInfo ? (
              <CreatorParameterForm
                creatorName={creatorInfo.class_name}
                creatorDescription={creatorInfo.description}
                params={creatorInfo.parameters}
                values={values}
                onChange={(key, value) => setValues((prev) => ({ ...prev, [key]: value }))}
                availableShapeKeys={creator.shapes
                  .filter((s) => s.direction === "output")
                  .map((s) => s.name)}
              />
            ) : (
              <p className="text-[12px] text-muted-foreground">
                Creator &quot;{creator.creatorClassName}&quot; not found in catalog.
              </p>
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-2 border-t border-border px-6 py-4">
            <button
              onClick={onClose}
              className="rounded-full border border-border px-4 py-2 text-[13px] text-muted-foreground hover:bg-sidebar-accent"
            >
              Cancel
            </button>
            <button
              onClick={onClose}
              className="rounded-full bg-primary px-4 py-2 text-[13px] text-primary-foreground hover:opacity-90"
            >
              Save
            </button>
          </div>
        </div>
      )}
    </dialog>
  );
}
