"use client";

import { useCallback } from "react";
import { useSWRConfig } from "swr";
import { patchSurfaceType, type SurfaceTypePatch } from "@/lib/surfaceType";

/**
 * Role-change action for wings (GH-1187). After a successful PATCH every
 * cached wing read of the aeroplane (useWing and useAllWingData keys) is
 * revalidated, because a swap changes two wings at once.
 */
export function useSurfaceTypeActions(aeroplaneId: string | null) {
  const { mutate } = useSWRConfig();

  const setSurfaceType = useCallback(
    async (wingName: string, body: SurfaceTypePatch) => {
      if (!aeroplaneId) throw new Error("No aeroplane selected.");
      await patchSurfaceType(aeroplaneId, wingName, body);
      await mutate(
        (key) =>
          typeof key === "string" &&
          (key.startsWith(`/aeroplanes/${aeroplaneId}/wings`) ||
            key.startsWith(`all-wings:${aeroplaneId}:`)),
      );
    },
    [aeroplaneId, mutate],
  );

  return { setSurfaceType };
}
