"use client";

import { useState } from "react";
import { ArrowRight, ArrowLeft, X, RotateCcw } from "lucide-react";
import { useDialog } from "@/hooks/useDialog";
import { CreatorParameterForm } from "@/components/workbench/CreatorParameterForm";
import type { CreatorInfo } from "@/hooks/useCreators";
import type { PlanStepNode } from "@/components/workbench/PlanTree";
import { resolveNodeShapes, resolveIdTemplate } from "@/lib/planTreeUtils";

interface EditParamsModalProps {
  open: boolean;
  node: PlanStepNode | null;
  nodePath: string | null;
  creatorInfo: CreatorInfo | null;
  availableShapeKeys: string[];
  onClose: () => void;
  onSave: (path: string, updatedParams: Record<string, unknown>) => Promise<void>;
}

function extractValues(
  node: PlanStepNode,
  creatorInfo: CreatorInfo,
): Record<string, unknown> {
  const vals: Record<string, unknown> = {};
  for (const param of creatorInfo.parameters) {
    if (param.name in node) vals[param.name] = (node as Record<string, unknown>)[param.name];
    else if (param.default != null) vals[param.name] = param.default;
  }
  // Always include loglevel (universal param)
  if ("loglevel" in node) vals.loglevel = (node as Record<string, unknown>).loglevel;
  return vals;
}

export function EditParamsModal({
  open,
  node,
  nodePath,
  creatorInfo,
  availableShapeKeys,
  onClose,
  onSave,
}: Readonly<EditParamsModalProps>) {
  const { dialogRef, handleClose } = useDialog(open, onClose);
  const [values, setValues] = useState<Record<string, unknown>>({});

  // Reset values when a different node is opened (track by nodePath for uniqueness)
  const [lastNodePath, setLastNodePath] = useState<string | null>(null);
  const [creatorId, setCreatorId] = useState("");
  const [creatorIdDirty, setCreatorIdDirty] = useState(false);

  if (open && node && nodePath !== lastNodePath) {
    setLastNodePath(nodePath);
    setValues(creatorInfo ? extractValues(node, creatorInfo) : {});
    setCreatorId(node.creator_id);
    setCreatorIdDirty(!!(node as Record<string, unknown>)._creatorIdDirty);
  }
  if (!open && lastNodePath !== null) {
    setLastNodePath(null);
  }

  const shapes = node && creatorInfo ? resolveNodeShapes(node, [creatorInfo]) : { inputs: [], outputs: [] };
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (nodePath == null) return;
    setSaving(true);
    try {
      await onSave(nodePath, { ...values, creator_id: creatorId, _creatorIdDirty: creatorIdDirty || undefined });
      onClose();
    } catch (err) {
      alert(`Save failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <dialog
      ref={dialogRef}
      className="m-auto bg-transparent backdrop:bg-black/60"
      onClose={handleClose}
      aria-label={node ? `Edit ${node.creator_id}` : "Edit Parameters"}
    >
      {open && node && (
        <div className="flex max-h-[85vh] w-[520px] flex-col rounded-2xl border border-border bg-card shadow-2xl">
          {/* Header */}
          <div className="flex items-center gap-3 border-b border-border px-6 py-4">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
              Edit {node.creator_id}
            </span>
            <span className="flex-1" />
            <button
              onClick={onClose}
              className="flex size-8 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
            >
              <X size={16} />
            </button>
          </div>

          {/* CreatorId field */}
          <div className="flex items-center gap-2 border-b border-border px-6 py-3">
            <label
              htmlFor="creator-id-input"
              className="shrink-0 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground"
            >
              ID
            </label>
            <input
              id="creator-id-input"
              type="text"
              value={creatorId}
              onChange={(e) => {
                setCreatorId(e.target.value);
                setCreatorIdDirty(true);
              }}
              className="flex-1 rounded-lg border border-border bg-card-muted/30 px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground outline-none focus:border-primary"
            />
            {creatorIdDirty && (
              <button
                type="button"
                onClick={() => {
                  setCreatorIdDirty(false);
                  if (creatorInfo?.suggested_id) {
                    setCreatorId(resolveIdTemplate(creatorInfo.suggested_id, values));
                  }
                }}
                title="Reset to auto-derived ID"
                className="flex size-6 shrink-0 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
              >
                <RotateCcw size={12} />
              </button>
            )}
          </div>

          {/* Body */}
          <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-6 py-5">
            {(shapes.inputs.length > 0 || shapes.outputs.length > 0) && (
              <div className="flex flex-col gap-1 rounded-xl border border-border bg-card-muted/30 p-3">
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
                  Shapes
                </span>
                {shapes.inputs.map((inp) => (
                  <div
                    key={`input-${inp.paramName}`}
                    className={`flex items-center gap-2 text-[12px] ${inp.boundValue ? "text-muted-foreground" : "text-red-400/70"}`}
                  >
                    <ArrowRight size={10} className={inp.boundValue ? "text-blue-400" : "text-red-400/50"} />
                    <span className="font-[family-name:var(--font-jetbrains-mono)]">
                      {inp.boundValue ?? inp.paramName}
                    </span>
                    <span className="text-[10px] text-subtle-foreground">
                      ({inp.boundValue ? inp.paramName : "unbound"})
                    </span>
                  </div>
                ))}
                {shapes.outputs.map((key) => (
                  <div
                    key={`output-${key}`}
                    className="flex items-center gap-2 text-[12px] text-muted-foreground"
                  >
                    <ArrowLeft size={10} className="text-emerald-400" />
                    <span className="font-[family-name:var(--font-jetbrains-mono)]">{key}</span>
                    <span className="text-[10px] text-subtle-foreground">(output)</span>
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
                onChange={(key, value) => {
                  const next = { ...values, [key]: value };
                  setValues(next);
                  if (!creatorIdDirty && creatorInfo?.suggested_id) {
                    setCreatorId(resolveIdTemplate(creatorInfo.suggested_id, next));
                  }
                }}
                availableShapeKeys={availableShapeKeys}
              />
            ) : (
              <p className="text-[12px] text-muted-foreground">
                Creator &quot;{node.$TYPE}&quot; not found in catalog.
              </p>
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-2 border-t border-border px-6 py-4">
            <button
              onClick={onClose}
              disabled={saving}
              className="rounded-full border border-border px-4 py-2 text-[13px] text-muted-foreground hover:bg-sidebar-accent disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="rounded-full bg-primary px-4 py-2 text-[13px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
            >
              {saving ? "Saving\u2026" : "Save"}
            </button>
          </div>
        </div>
      )}
    </dialog>
  );
}
