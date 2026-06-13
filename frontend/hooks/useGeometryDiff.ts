"use client";

import { useMemo } from "react";
import useSWR from "swr";

import { fetcher } from "@/lib/fetcher";
import type { WingConfig } from "@/hooks/useWingConfig";
import {
  computeGeometryDiff,
  type DiffWingInput,
  type GeometryDiff,
} from "@/lib/geometryDiff";

/**
 * Lazy geometry-parameter diff for the version-compare view (gh-971).
 *
 * When `enabled` is false (the "Geometry changes" section is collapsed) this
 * fetches NOTHING — the SWR key is null and `diff` is null. When enabled and
 * both node UUIDs are present, it fetches every wing's WingConfig for both
 * compared nodes (existing endpoint, mm units) and memoises a pure
 * `computeGeometryDiff` over the results.
 *
 * `wingNames` is the union of both sides' wing names. A wing present on only
 * one node yields a null config on the missing side (added/removed), which the
 * pure diff handles by aligning on wing name.
 *
 * 404 handling: a 404 from one side means that wing is absent on that node
 * (added or removed). `fetchConfigOrNull` catches 404 errors and returns null
 * rather than propagating the error, so the diff can report added/removed
 * correctly. Other HTTP errors still propagate to the SWR error state.
 */

function wingconfigPath(uuid: string, wingName: string): string {
  return `/aeroplanes/${uuid}/wings/${wingName}/wingconfig`;
}

/** One fetched wing config keyed by node and name (null = absent for that node). */
interface FetchedWing {
  name: string;
  configA: WingConfig | null;
  configB: WingConfig | null;
}

/**
 * Fetch a WingConfig, returning null for 404 (wing absent on this node).
 * Other errors are rethrown so SWR can surface them.
 */
async function fetchConfigOrNull(
  uuid: string,
  name: string,
): Promise<WingConfig | null> {
  try {
    return await fetcher<WingConfig>(wingconfigPath(uuid, name));
  } catch (err) {
    if (err instanceof Error) {
      const m = err.message.match(/^(\d{3})\b/);
      if (m && m[1] === "404") return null;
    }
    throw err;
  }
}

/**
 * Fetch every (node, wing) WingConfig in parallel. A null config means the
 * endpoint returned 404 for that side (wing absent); other failures propagate
 * so SWR surfaces them as `error`.
 */
async function fetchAllConfigs(
  uuidA: string,
  uuidB: string,
  wingNames: string[],
): Promise<FetchedWing[]> {
  return Promise.all(
    wingNames.map(async (name) => {
      const [configA, configB] = await Promise.all([
        fetchConfigOrNull(uuidA, name),
        fetchConfigOrNull(uuidB, name),
      ]);
      return { name, configA, configB };
    }),
  );
}

function toDiffInputs(fetched: FetchedWing[]): {
  wingsA: DiffWingInput[];
  wingsB: DiffWingInput[];
} {
  const wingsA: DiffWingInput[] = [];
  const wingsB: DiffWingInput[] = [];
  for (const { name, configA, configB } of fetched) {
    if (configA) wingsA.push({ name, config: configA });
    if (configB) wingsB.push({ name, config: configB });
  }
  return { wingsA, wingsB };
}

export interface UseGeometryDiffResult {
  diff: GeometryDiff | null;
  isLoading: boolean;
  error: Error | null;
}

export function useGeometryDiff(
  nodeAUuid: string | null,
  nodeBUuid: string | null,
  wingNames: string[],
  enabled: boolean,
  showAll: boolean = false,
): UseGeometryDiffResult {
  // De-duplicate while preserving original order for fetch + diff.
  // Sort only for the SWR cache key (stability); the fetch order stays
  // as the caller provided so wing display order is preserved.
  const dedupedNames = useMemo(
    () => Array.from(new Set(wingNames)),
    [wingNames],
  );

  // Stable, sorted key string for SWR cache consistency.
  const sortedKey = useMemo(
    () => [...dedupedNames].sort((a, b) => a.localeCompare(b)).join(" "),
    [dedupedNames],
  );

  const swrKey =
    enabled && nodeAUuid && nodeBUuid && dedupedNames.length > 0
      ? (["geometry-diff", nodeAUuid, nodeBUuid, sortedKey] as const)
      : null;

  const { data, error, isLoading } = useSWR<FetchedWing[], Error>(
    swrKey,
    () => fetchAllConfigs(nodeAUuid as string, nodeBUuid as string, dedupedNames),
    { shouldRetryOnError: false },
  );

  const diff = useMemo<GeometryDiff | null>(() => {
    if (!data) return null;
    const { wingsA, wingsB } = toDiffInputs(data);
    return computeGeometryDiff(wingsA, wingsB, { showAll });
  }, [data, showAll]);

  return {
    diff,
    isLoading: swrKey != null && isLoading,
    error: error ?? null,
  };
}
