"use client";

import { ActionRow } from "./ActionRow";
import { PropertyForm } from "./PropertyForm";
import { useWings } from "@/hooks/useWings";

interface ConfigPanelProps {
  aeroplaneId: string;
  onGeometryChanged?: (wingName: string) => void;
  onFuselageSaved?: () => void;
}

export function ConfigPanel({ aeroplaneId, onGeometryChanged, onFuselageSaved }: ConfigPanelProps) {
  const { mutate: mutateWings } = useWings(aeroplaneId);

  return (
    <aside className="flex h-full flex-col gap-4 p-4">
      <ActionRow aeroplaneId={aeroplaneId} onWingCreated={() => mutateWings()} onFuselageSaved={onFuselageSaved} />
      <div className="min-h-0 flex-1 overflow-y-auto">
        <PropertyForm onGeometryChanged={onGeometryChanged} />
      </div>
    </aside>
  );
}
