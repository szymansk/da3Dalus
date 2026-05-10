"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";

type RecomputeJobStatus = "idle" | "debouncing" | "computing" | "done" | "failed";

interface RecomputeStatusResponse {
  status: RecomputeJobStatus;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
}

/**
 * Polls the per-aircraft assumption-recompute job status. While a job
 * is in flight (debouncing or computing), `isRecomputing` is true so
 * the UI can show a spinner regardless of which event triggered the
 * recompute (geometry change, mass change, SM change, weight items …).
 */
export function useRecomputeStatus(aeroplaneId: string | null) {
  const path = aeroplaneId
    ? `/aeroplanes/${encodeURIComponent(aeroplaneId)}/assumptions/recompute-status`
    : null;

  const { data } = useSWR<RecomputeStatusResponse>(path, fetcher, {
    refreshInterval: 1500,
    revalidateOnFocus: false,
    dedupingInterval: 0,
  });

  const isRecomputing =
    data?.status === "debouncing" || data?.status === "computing";

  return {
    isRecomputing,
    status: data?.status ?? "idle",
    error: data?.error ?? null,
  };
}
