"use client";

import { Play, Plus, Download } from "lucide-react";
import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useWings } from "@/hooks/useWings";
import { API_BASE } from "@/lib/fetcher";

interface ActionRowProps {
  aeroplaneId: string | null;
  onWingCreated?: () => void;
}

export function ActionRow({ aeroplaneId, onWingCreated }: ActionRowProps) {
  const ctx = useAeroplaneContext();
  const { mutate: mutateWings } = useWings(aeroplaneId);

  async function handleAddWing() {
    if (!aeroplaneId) return;
    const name = prompt("Wing name?");
    if (!name) return;

    // A wing needs at least 2 x_secs (root + tip) for valid ASB geometry
    const rootXSec = {
      xyz_le: [0, 0, 0],
      chord: 0.15,
      twist: 0,
      airfoil: "naca0012",
    };
    const tipXSec = {
      xyz_le: [0, 0.5, 0],
      chord: 0.12,
      twist: 0,
      airfoil: "naca0012",
    };

    const res = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${encodeURIComponent(name)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          symmetric: true,
          x_secs: [rootXSec, tipXSec],
        }),
      },
    );

    if (!res.ok) {
      alert(`Failed to create wing: ${res.status}`);
      return;
    }

    await mutateWings();
    ctx.selectWing(name);
    onWingCreated?.();
  }

  function handleAddFuselage() {
    if (!aeroplaneId) {
      alert("Select an aeroplane first.");
      return;
    }
    const name = prompt("Fuselage name?");
    if (!name) return;
    alert(`Fuselage creation not yet connected (name: ${name})`);
  }

  function handlePreviewSTL() {
    alert("STL preview not yet connected");
  }

  function handleDownloadSTEP() {
    alert("STEP download not yet connected");
  }

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handlePreviewSTL}
        className="flex items-center gap-2 rounded-full bg-primary px-4 py-2.5 text-[13px] text-primary-foreground hover:opacity-90"
      >
        <Play size={14} />
        <span>Preview STL</span>
      </button>
      <button
        onClick={handleAddWing}
        className="flex items-center gap-1.5 rounded-full border border-border bg-card-muted px-3.5 py-2.5 text-[13px] text-foreground hover:bg-sidebar-accent"
      >
        <Plus size={14} />
        <span>Wing</span>
      </button>
      <button
        onClick={handleAddFuselage}
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
    </div>
  );
}
