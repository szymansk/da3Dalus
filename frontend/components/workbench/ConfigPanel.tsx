"use client";

import { ActionRow } from "./ActionRow";
import { AeroplaneTree } from "./AeroplaneTree";
import { PropertyForm } from "./PropertyForm";

export function ConfigPanel() {
  return (
    <aside className="flex w-[556px] shrink-0 flex-col gap-4 overflow-y-auto p-4">
      <ActionRow />
      <AeroplaneTree />
      <PropertyForm />
    </aside>
  );
}
