"use client";

import { ActionRow } from "./ActionRow";
import { PropertyForm } from "./PropertyForm";
import { useWings } from "@/hooks/useWings";

interface ConfigPanelProps {
  aeroplaneId: string;
  onGeometryChanged?: (wingName: string) => void;
}

export function ConfigPanel({ aeroplaneId, onGeometryChanged }: ConfigPanelProps) {
  const { mutate: mutateWings } = useWings(aeroplaneId);

  return (
    <aside className="flex h-full flex-col gap-4 p-4">
      <ActionRow aeroplaneId={aeroplaneId} onWingCreated={() => mutateWings()} />
      <div className="min-h-0 flex-1 overflow-y-auto">
        <PropertyForm onGeometryChanged={onGeometryChanged} />
      </div>
    </aside>
  );
}
