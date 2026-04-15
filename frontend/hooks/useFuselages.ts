"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";

export function useFuselages(aeroplaneId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<string[]>(
    aeroplaneId ? `/aeroplanes/${aeroplaneId}/fuselages` : null,
    fetcher,
  );

  return {
    fuselageNames: data ?? [],
    error,
    isLoading,
    mutate,
  };
}
