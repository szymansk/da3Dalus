"use client";

import { useState, useCallback, useRef } from "react";
import { API_BASE } from "@/lib/fetcher";

interface WingPreview {
  visible: boolean;
  data: Record<string, unknown> | null;
  loading: boolean;
  error: string | null;
  /** geometry hash — set after tessellation to detect staleness */
  hash: string;
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

  const getVisibleParts = useCallback((): Record<string, unknown>[] => {
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

      // Cancel any running tessellation for this wing
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

        // Poll for completion
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
              [wingName]: {
                visible: true,
                data: s.result,
                loading: false,
                error: null,
                hash: s.result?.data?.shapes?.bb ? JSON.stringify(s.result.data.shapes.bb) : "",
              },
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

  /** Toggle preview on/off for a wing. If toggling on and no cache, tessellate. */
  const toggleWing = useCallback(
    (wingName: string) => {
      setPreviews((prev) => {
        const existing = prev[wingName];
        if (existing?.visible) {
          // Toggle off — keep cache, just hide
          return { ...prev, [wingName]: { ...existing, visible: false } };
        }
        // Toggle on
        if (existing?.data) {
          // Cache hit — just show
          return { ...prev, [wingName]: { ...existing, visible: true } };
        }
        // No cache — mark visible, tessellation will be triggered below
        return {
          ...prev,
          [wingName]: { visible: true, data: null, loading: false, error: null, hash: "" },
        };
      });

      // If no cached data, trigger tessellation (outside setState)
      const existing = previews[wingName];
      if (!existing?.visible && !existing?.data) {
        tessellateWing(wingName);
      }
    },
    [previews, tessellateWing],
  );

  /** Invalidate cache for a wing. If visible, re-tessellate. */
  const invalidateWing = useCallback(
    (wingName: string) => {
      setPreviews((prev) => {
        const existing = prev[wingName];
        if (!existing) return prev;
        const updated = { ...existing, data: null, hash: "" };
        return { ...prev, [wingName]: updated };
      });
      // If wing was visible, re-tessellate
      if (previews[wingName]?.visible) {
        tessellateWing(wingName);
      }
    },
    [previews, tessellateWing],
  );

  /** Check if a wing's preview is toggled on. */
  const isWingVisible = useCallback(
    (wingName: string): boolean => previews[wingName]?.visible ?? false,
    [previews],
  );

  return {
    previews,
    getVisibleParts,
    toggleWing,
    invalidateWing,
    isWingVisible,
    isAnyLoading,
    loadingWing,
  };
}
