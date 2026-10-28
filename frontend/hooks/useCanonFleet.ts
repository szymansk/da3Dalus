"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";
import type { CanonFleetEntry } from "@/types/canon";

/** The reference-fleet aircraft the Expert View can load (kernel reference fleet). */
export function useCanonFleet() {
  const { data, error, isLoading } = useSWR<CanonFleetEntry[]>(
    "/canon/fleet",
    fetcher,
  );
  return { fleet: data ?? [], error, isLoading };
}
