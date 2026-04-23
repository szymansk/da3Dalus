"use client";

import { useState } from "react";
import { Plus, Download } from "lucide-react";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useWings } from "@/hooks/useWings";
import { ImportFuselageDialog } from "./ImportFuselageDialog";
import { CreateWingDialog } from "./CreateWingDialog";

interface ActionRowProps {
  aeroplaneId: string | null;
  onWingCreated?: () => void;
  onFuselageSaved?: () => void;
}

export function ActionRow({ aeroplaneId, onWingCreated, onFuselageSaved }: Readonly<ActionRowProps>) {
  const ctx = useAeroplaneContext();
  const { mutate: mutateWings } = useWings(aeroplaneId);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [createWingOpen, setCreateWingOpen] = useState(false);

  function handleDownloadSTEP() {
    alert("STEP download not yet connected");
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        onClick={() => setCreateWingOpen(true)}
        className="flex items-center gap-1.5 rounded-full border border-border bg-card-muted px-3.5 py-2.5 text-[13px] text-foreground hover:bg-sidebar-accent"
      >
        <Plus size={14} />
        <span>Wing</span>
      </button>
      <button
        onClick={() => setImportDialogOpen(true)}
        className="flex items-center gap-1.5 rounded-full border border-border bg-card-muted px-3.5 py-2.5 text-[13px] text-foreground hover:bg-sidebar-accent"
      >
        <Plus size={14} />
        <span>Fuselage</span>
      </button>
      <button
        onClick={handleDownloadSTEP}
        className="flex items-center gap-1.5 rounded-full border border-border-strong bg-background px-3.5 py-2.5 text-[13px] text-foreground hover:bg-sidebar-accent"
      >
        <Download size={14} />
        <span>Download STEP</span>
      </button>

      <CreateWingDialog
        open={createWingOpen}
        onClose={() => setCreateWingOpen(false)}
        aeroplaneId={aeroplaneId}
        onCreated={async (wingName, designModel) => {
          await mutateWings();
          ctx.selectWing(wingName);
          ctx.setTreeMode(designModel === "wc" ? "wingconfig" : "asb");
          onWingCreated?.();
        }}
      />

      <ImportFuselageDialog
        open={importDialogOpen}
        onClose={() => setImportDialogOpen(false)}
        aeroplaneId={aeroplaneId}
        onSaved={() => {
          onFuselageSaved?.();
        }}
      />
    </div>
  );
}
