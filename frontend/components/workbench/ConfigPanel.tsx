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
    <aside className="flex w-[556px] shrink-0 flex-col gap-4 overflow-y-auto p-4">
      <ActionRow aeroplaneId={aeroplaneId} onWingCreated={() => mutateWings()} />
      <AeroplaneTree
        aeroplaneId={aeroplaneId}
        wingNames={wingNames}
        aeroplaneName={aeroplaneName}
      />
      <PropertyForm />
    </aside>
  );
}
