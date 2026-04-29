"use client";

import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useAeroplanes } from "@/hooks/useAeroplanes";
import { AeroplanePickerDialog } from "@/components/workbench/construction-plans/AeroplanePickerDialog";

export function AeroplanePickerHost() {
  const { aeroplaneId, setAeroplaneId, pickerOpen, closePicker } = useAeroplaneContext();
  const { aeroplanes, createAeroplane, deleteAeroplane } = useAeroplanes();

  return (
    <AeroplanePickerDialog
      open={pickerOpen}
      aeroplanes={aeroplanes}
      title="Select Aeroplane"
      selectedAeroplaneId={aeroplaneId}
      onClose={closePicker}
      onSelect={async (id) => {
        setAeroplaneId(id);
        closePicker();
      }}
      onDelete={async (id) => {
        await deleteAeroplane(id);
        if (id === aeroplaneId) {
          setAeroplaneId(null);
        }
      }}
      onCreate={async (name) => {
        const created = await createAeroplane(name);
        if (!created?.id) throw new Error("Server returned aeroplane without an ID");
        setAeroplaneId(created.id);
        closePicker();
      }}
    />
  );
}
