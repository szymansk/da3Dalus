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

  const isAnyLoading = Object.values(previews).some((p) => p.loading);
  const loadingWing = Object.entries(previews).find(([, p]) => p.loading)?.[0] ?? null;

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

  // Fix #1: Stale closure — decide inside setPreviews updater, trigger side-effect via flag
  const toggleWing = useCallback(
    (wingName: string) => {
      let needsTessellation = false;
      setPreviews((prev) => {
        const existing = prev[wingName];
        if (existing?.visible) {
          return { ...prev, [wingName]: { ...existing, visible: false } };
        }
        if (existing?.data) {
          return { ...prev, [wingName]: { ...existing, visible: true } };
        }
        needsTessellation = true;
        return {
          ...prev,
          [wingName]: { visible: true, data: null, loading: false, error: null },
        };
      });
      if (needsTessellation) {
        tessellateWing(wingName);
      }
    },
    [tessellateWing],
  );

  // Fix #2: Stale closure — decide inside setPreviews updater
  const invalidateWing = useCallback(
    (wingName: string) => {
      let wasVisible = false;
      setPreviews((prev) => {
        const existing = prev[wingName];
        if (!existing) return prev;
        wasVisible = existing.visible;
        return { ...prev, [wingName]: { ...existing, data: null } };
      });
      if (wasVisible) {
        tessellateWing(wingName);
      }
    },
    [tessellateWing],
  );

  const isWingVisible = useCallback(
    (wingName: string): boolean => previews[wingName]?.visible ?? false,
    [previews],
  );

  return {
    previews,
    visibleParts,
    toggleWing,
    invalidateWing,
    isWingVisible,
    isAnyLoading,
    loadingWing,
  };
}
