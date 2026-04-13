"use client";

import { ActionRow } from "./ActionRow";
import { AeroplaneTree } from "./AeroplaneTree";
import { PropertyForm } from "./PropertyForm";
import { useWings } from "@/hooks/useWings";
import { useAeroplanes } from "@/hooks/useAeroplanes";

interface ConfigPanelProps {
  aeroplaneId: string;
}

export function ConfigPanel({ aeroplaneId }: ConfigPanelProps) {
  const { wingNames, mutate: mutateWings } = useWings(aeroplaneId);
  const { aeroplanes } = useAeroplanes();
  const aeroplaneName =
    aeroplanes.find((a) => a.id === aeroplaneId)?.name ?? "Aeroplane";

  return (
    <aside className="flex h-full flex-col gap-4 p-4">
      <ActionRow aeroplaneId={aeroplaneId} onWingCreated={() => mutateWings()} />
      <div className="min-h-0 flex-1 overflow-y-auto">
        <AeroplaneTree
          aeroplaneId={aeroplaneId}
          wingNames={wingNames}
          aeroplaneName={aeroplaneName}
        />
      </div>
      <div className="shrink-0">
        <PropertyForm />
      </div>
    </aside>
  );
}
