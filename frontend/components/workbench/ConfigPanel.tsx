"use client";

import { ActionRow } from "./ActionRow";
import { AeroplaneTree } from "./AeroplaneTree";
import { PropertyForm } from "./PropertyForm";
import { useWings } from "@/hooks/useWings";
import { useAeroplanes } from "@/hooks/useAeroplanes";

interface ConfigPanelProps {
  aeroplaneId: string;
  isWingVisible?: (wingName: string) => boolean;
  isWingLoading?: (wingName: string) => boolean;
  onTogglePreview?: (wingName: string) => void;
  onToggleAllPreview?: (wingNames: string[]) => void;
  onGeometryChanged?: (wingName: string) => void;
}

export function ConfigPanel({ aeroplaneId, isWingVisible, isWingLoading, onTogglePreview, onToggleAllPreview, onGeometryChanged }: ConfigPanelProps) {
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
          isWingVisible={isWingVisible}
          isWingLoading={isWingLoading}
          onTogglePreview={onTogglePreview}
          onToggleAllPreview={onToggleAllPreview}
        />
      </div>
      <div className="shrink-0">
        <PropertyForm onGeometryChanged={onGeometryChanged} />
      </div>
    </aside>
  );
}
