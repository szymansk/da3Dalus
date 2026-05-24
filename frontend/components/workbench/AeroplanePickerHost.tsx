"use client";

import { useSWRConfig } from "swr";

import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useAeroplanes } from "@/hooks/useAeroplanes";
import { AeroplanePickerDialog } from "@/components/workbench/construction-plans/AeroplanePickerDialog";

export function AeroplanePickerHost() {
  const {
    aeroplaneId,
    setAeroplaneId,
    pickerOpen,
    closePicker,
    setLastImportWarnings,
  } = useAeroplaneContext();
  const { aeroplanes, createAeroplane, deleteAeroplane, mutate } =
    useAeroplanes();
  const { mutate: globalMutate } = useSWRConfig();

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
      onImport={(response) => {
        // gh-695: select the freshly-imported aeroplane, persist its
        // warnings in context so the workbench layout banner picks
        // them up, refresh the aeroplane list, and close the dialog.
        setLastImportWarnings({
          uuid: response.aeroplane_uuid,
          warnings: response.warnings,
        });
        setAeroplaneId(response.aeroplane_uuid);
        // Refresh the local aeroplane list + any wing/fuselage data
        // hooks keyed off the new uuid so the workbench renders the
        // imported geometry immediately.
        mutate();
        globalMutate(
          (key) =>
            typeof key === "string" &&
            key.includes(response.aeroplane_uuid),
        );
        closePicker();
      }}
    />
  );
}
