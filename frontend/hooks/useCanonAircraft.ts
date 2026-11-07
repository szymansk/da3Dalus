"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";
import type { CanonAircraftList } from "@/types/canon";

/** The aircraft the Expert View can load: the kernel's reference fleet and the stored aeroplanes. */
export function useCanonAircraft() {
  const { data, error, isLoading } = useSWR<CanonAircraftList>("/canon/aircraft", fetcher);
  return {
    fleet: data?.fleet ?? [],
    aeroplanes: data?.aeroplanes ?? [],
    error,
    isLoading,
  };
}
