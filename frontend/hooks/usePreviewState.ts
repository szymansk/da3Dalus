"use client";

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { API_BASE } from "@/lib/fetcher";

interface WingPreview {
  visible: boolean;
  data: Record<string, unknown> | null;
  loading: boolean;
  error: string | null;
}

type PreviewMap = Record<string, WingPreview>;

/**
 * Manages per-wing 3D preview visibility and tessellation cache.
 *
 * Each wing can be toggled on/off independently. Toggling on triggers
 * tessellation if no cached data exists. Geometry changes invalidate
 * the cache for that wing — if it's visible, it re-tessellates automatically.
 */
export function usePreviewState(aeroplaneId: string | null) {
  const [previews, setPreviews] = useState<PreviewMap>({});
  const abortControllers = useRef<Record<string, AbortController>>({});

  // Fix #5: Reset state + abort in-flight requests when aeroplane changes
  useEffect(() => {
    setPreviews({});
    Object.values(abortControllers.current).forEach((c) => c.abort());
    abortControllers.current = {};
  }, [aeroplaneId]);

  // Fix #3: Memoize visible parts by comparing data references, not array identity
  const visibleParts = useMemo((): Record<string, unknown>[] => {
    return Object.values(previews)
      .filter((p) => p.visible && p.data)
      .map((p) => p.data!);
  }, [previews]);

  const isAnyLoading = useMemo(() => Object.values(previews).some((p) => p.loading), [previews]);
  const loadingWing = useMemo(() => Object.entries(previews).find(([, p]) => p.loading)?.[0] ?? null, [previews]);

  /** Tessellate a single wing and store the result. */
  const tessellateWing = useCallback(
    async (wingName: string) => {
      if (!aeroplaneId) return;

      abortControllers.current[wingName]?.abort();
      const controller = new AbortController();
      abortControllers.current[wingName] = controller;
      const signal = controller.signal;

      setPreviews((prev) => ({
        ...prev,
        [wingName]: { ...prev[wingName], visible: true, loading: true, error: null },
      }));

      try {
        const encodedWing = encodeURIComponent(wingName);

        const postRes = await fetch(
          `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${encodedWing}/tessellation`,
          { method: "POST", signal },
        );
        if (!postRes.ok) throw new Error(`Tessellation failed: ${postRes.status}`);

        const deadline = Date.now() + 120_000;
        while (Date.now() < deadline) {
          if (signal.aborted) return;
          const r = await fetch(
            `${API_BASE}/aeroplanes/${aeroplaneId}/status?task_type=tessellation&wing_name=${encodedWing}`,
            { signal },
          );
          const s = await r.json();

          if (s.status === "SUCCESS" && s.result?.data) {
            setPreviews((prev) => ({
              ...prev,
              [wingName]: { visible: true, data: s.result, loading: false, error: null },
            }));
            return;
          }
          if (s.status === "FAILURE") {
            throw new Error(s.message || "Tessellation failed");
          }
          await new Promise((resolve) => setTimeout(resolve, 500));
        }
        throw new Error("Tessellation timed out");
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setPreviews((prev) => ({
          ...prev,
          [wingName]: {
            ...prev[wingName],
            loading: false,
            error: err instanceof Error ? err.message : String(err),
          },
        }));
      }
    },
    [aeroplaneId],
  );

  /** Toggle preview on/off. Reads current state before updating to avoid
   *  stale-closure issues with React 19 automatic batching. */
  const toggleWing = useCallback(
    (wingName: string) => {
      const existing = previews[wingName];
      if (existing?.visible) {
        setPreviews((prev) => ({ ...prev, [wingName]: { ...prev[wingName], visible: false } }));
      } else if (existing?.data) {
        setPreviews((prev) => ({ ...prev, [wingName]: { ...prev[wingName], visible: true } }));
      } else {
        setPreviews((prev) => ({
          ...prev,
          [wingName]: { visible: true, data: null, loading: false, error: null },
        }));
        tessellateWing(wingName);
      }
    },
    [previews, tessellateWing],
  );

  /** Toggle all wings at once — one atomic state update, then tessellate uncached. */
  const toggleAllWings = useCallback(
    (wingNames: string[]) => {
      const anyVisible = wingNames.some((wn) => previews[wn]?.visible);
      const toTessellate: string[] = [];

      if (anyVisible) {
        // Hide all
        setPreviews((prev) => {
          const next = { ...prev };
          for (const wn of wingNames) {
            if (next[wn]) next[wn] = { ...next[wn], visible: false };
          }
          return next;
        });
      } else {
        // Show all — determine which need tessellation before updating state
        for (const wn of wingNames) {
          if (!previews[wn]?.data) toTessellate.push(wn);
        }
        setPreviews((prev) => {
          const next = { ...prev };
          for (const wn of wingNames) {
            if (prev[wn]?.data) {
              next[wn] = { ...prev[wn], visible: true };
            } else {
              next[wn] = { visible: true, data: null, loading: false, error: null };
            }
          }
          return next;
        });
        for (const wn of toTessellate) {
          tessellateWing(wn);
        }
      }
    },
    [previews, tessellateWing],
  );

  /** Invalidate cache for a wing. If visible, re-tessellate. */
  const invalidateWing = useCallback(
    (wingName: string) => {
      const wasVisible = previews[wingName]?.visible ?? false;
      setPreviews((prev) => {
        const existing = prev[wingName];
        if (!existing) return prev;
        return { ...prev, [wingName]: { ...existing, data: null } };
      });
      if (wasVisible) {
        tessellateWing(wingName);
      }
    },
    [previews, tessellateWing],
  );

  const isWingVisible = useCallback(
    (wingName: string): boolean => previews[wingName]?.visible ?? false,
    [previews],
  );

  return {
    previews,
    visibleParts,
    toggleWing,
    toggleAllWings,
    invalidateWing,
    isWingVisible,
    isAnyLoading,
    loadingWing,
  };
}
