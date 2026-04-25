"use client";

import { useState } from "react";
import { X, FileText, BookTemplate } from "lucide-react";
import { useDialog } from "@/hooks/useDialog";
import type { PlanSummary } from "@/hooks/useConstructionPlans";

interface NewPlanDialogProps {
  open: boolean;
  templates: PlanSummary[];
  onClose: () => void;
  onCreateEmpty: () => Promise<void> | void;
  onCreateFromTemplate: (templateId: number) => Promise<void> | void;
}

export function NewPlanDialog({
  open,
  templates,
  onClose,
  onCreateEmpty,
  onCreateFromTemplate,
}: Readonly<NewPlanDialogProps>) {
  const { dialogRef, handleClose } = useDialog(open, onClose);
  const [submitting, setSubmitting] = useState(false);

  async function handleChoice(action: () => Promise<void> | void) {
    setSubmitting(true);
    try {
      await action();
      onClose();
    } catch (err) {
      alert(`Create plan failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <dialog
      ref={dialogRef}
      className="m-auto bg-transparent backdrop:bg-black/60"
      onClose={handleClose}
      aria-label="Create new plan"
    >
      {open && (
        <div className="flex w-[400px] flex-col rounded-2xl border border-border bg-card shadow-2xl">
          {/* Header */}
          <div className="flex items-center gap-3 border-b border-border px-6 py-4">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-foreground">
              New Construction Plan
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
          <div className="flex flex-col gap-2 px-6 py-5">
            <button
              onClick={() => handleChoice(onCreateEmpty)}
              disabled={submitting}
              className="flex items-center gap-3 rounded-xl border border-border px-4 py-3 text-left hover:bg-sidebar-accent disabled:opacity-50"
            >
              <FileText size={16} className="text-primary" />
              <div>
                <p className="text-[13px] font-medium text-foreground">Empty plan</p>
                <p className="text-[11px] text-muted-foreground">Start from scratch</p>
              </div>
            </button>

            {templates.length > 0 && (
              <>
                <p className="mt-2 px-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] uppercase tracking-wide text-muted-foreground">
                  From template
                </p>
                {templates.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => handleChoice(() => onCreateFromTemplate(t.id))}
                    disabled={submitting}
                    className="flex items-center gap-3 rounded-xl border border-border px-4 py-3 text-left hover:bg-sidebar-accent disabled:opacity-50"
                  >
                    <BookTemplate size={16} className="text-muted-foreground" />
                    <div>
                      <p className="text-[13px] text-foreground">{t.name}</p>
                      <p className="text-[11px] text-muted-foreground">{t.step_count} steps</p>
                    </div>
                  </button>
                ))}
              </>
            )}
          </div>
        </div>
      )}
    </dialog>
  );
}
