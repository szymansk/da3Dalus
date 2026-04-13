"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import useSWR from "swr";
import { fetcher, API_BASE } from "@/lib/fetcher";

interface TessellationState {
  data: Record<string, unknown> | null;
  isTessellating: boolean;
  progress: string;
  error: string | null;
  isStale: boolean;
}

interface AssembledScene {
  data: { shapes: Record<string, unknown>; instances: unknown[] };
  type: string;
  config: Record<string, unknown>;
  count: number;
  is_stale: boolean;
}

/**
 * Tessellation hook with server-side cache support.
 *
 * Flow:
 * 1. On mount: GET /tessellation → load cached scene (instant)
 * 2. If is_stale: poll every 3s until fresh
 * 3. Manual trigger: POST /tessellation → poll status → update cache
 * 4. After any wing save: cache invalidated server-side, hook detects
 *    is_stale on next poll and shows "Updating..." indicator
 */
export function useTessellation(aeroplaneId: string | null) {
  const [manualState, setManualState] = useState<{
    isTessellating: boolean;
    progress: string;
    error: string | null;
  }>({ isTessellating: false, progress: "", error: null });

  const abortRef = useRef<AbortController | null>(null);

  // SWR key is null initially — no auto-fetch of the large tessellation
  // payload on page load. Data is loaded only after triggerTessellation
  // succeeds or when the user explicitly requests it.
  const [swrKey, setSwrKey] = useState<string | null>(null);
  const { data: cached, error: fetchError, mutate } = useSWR<AssembledScene>(
    swrKey,
    fetcher,
    {
      refreshInterval: (data) => {
        if (data?.is_stale) return 3000;
        return 0;
      },
      revalidateOnFocus: false,
      shouldRetryOnError: false,
    },
  );

  // Manual trigger for first tessellation or refresh
  const triggerTessellation = useCallback(
    async (wingName: string) => {
      if (!aeroplaneId || !wingName) return;

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      const signal = controller.signal;

      setManualState({ isTessellating: true, progress: "Starting tessellation…", error: null });

      try {
        const encodedWing = encodeURIComponent(wingName);
        const postRes = await fetch(
          `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${encodedWing}/tessellation`,
          { method: "POST", signal },
        );
        if (!postRes.ok) {
          throw new Error(`Tessellation trigger failed: ${postRes.status}`);
        }

        setManualState((s) => ({ ...s, progress: "Tessellating geometry…" }));

        // Poll task status
        const deadline = Date.now() + 120_000;
        while (Date.now() < deadline) {
          if (signal.aborted) return;
          const statusRes = await fetch(
            `${API_BASE}/aeroplanes/${aeroplaneId}/status?task_type=tessellation`,
            { signal },
          );
          if (!statusRes.ok) throw new Error(`Status check failed: ${statusRes.status}`);
          const statusData = await statusRes.json();

          if (statusData.status === "SUCCESS") {
            // Enable SWR key and fetch the cached tessellation
            const key = `/aeroplanes/${aeroplaneId}/tessellation`;
            setSwrKey(key);
            await mutate();
            setManualState({ isTessellating: false, progress: "", error: null });
            return;
          }
          if (statusData.status === "FAILURE") {
            throw new Error(statusData.message || "Tessellation failed");
          }

          await new Promise((r) => setTimeout(r, 500));
        }
        throw new Error("Tessellation timed out");
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setManualState({
          isTessellating: false,
          progress: "",
          error: err instanceof Error ? err.message : String(err),
        });
      }
    },
    [aeroplaneId, mutate],
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const is404 = fetchError?.message?.includes("404");

  return {
    data: cached ?? null,
    isTessellating: manualState.isTessellating,
    progress: manualState.progress,
    error: is404 ? null : (manualState.error || fetchError?.message || null),
    isStale: cached?.is_stale ?? false,
    hasCachedData: !!cached && !is404,
    triggerTessellation,
  };
}
