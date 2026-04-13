"use client";

import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import { API_BASE } from "@/lib/fetcher";

interface TessellationState {
  data: Record<string, unknown> | null;
  isTessellating: boolean;
  progress: string;
  error: string | null;
}

interface CacheEntry {
  aeroplaneId: string;
  wingName: string;
  updatedAt: string;
  data: Record<string, unknown>;
}

/** In-memory cache keyed by aeroplaneId+wingName+updatedAt */
const tessellationCache = new Map<string, CacheEntry>();

function cacheKey(aeroplaneId: string, wingName: string): string {
  return `${aeroplaneId}/${wingName}`;
}

/** Clear the in-memory tessellation cache for a specific wing.
 *  Call after saving geometry changes so "Preview 3D" re-appears. */
export function invalidateTessellationCache(aeroplaneId: string, wingName: string): void {
  tessellationCache.delete(cacheKey(aeroplaneId, wingName));
}

export function useTessellation(aeroplaneId: string | null, wingName: string | null) {
  const [state, setState] = useState<TessellationState>({
    data: null,
    isTessellating: false,
    progress: "",
    error: null,
  });
  const lastKeyRef = useRef<string>("");
  const abortRef = useRef<AbortController | null>(null);

  // Auto-load from cache when aeroplaneId/wingName change
  useEffect(() => {
    if (!aeroplaneId || !wingName) {
      setState({ data: null, isTessellating: false, progress: "", error: null });
      return;
    }

    const key = cacheKey(aeroplaneId, wingName);
    if (key === lastKeyRef.current && state.data) return; // same wing, already showing
    lastKeyRef.current = key;

    const cached = tessellationCache.get(key);
    if (cached) {
      // Check if still valid by comparing updatedAt with the API
      setState({ data: cached.data, isTessellating: false, progress: "", error: null });

      // Validate in background — if aeroplane updated_at changed, invalidate
      fetch(`${API_BASE}/aeroplanes/${aeroplaneId}`)
        .then((r) => r.json())
        .then((aeroplane) => {
          if (aeroplane.updated_at !== cached.updatedAt) {
            // Geometry changed — clear cache, user needs to re-preview
            tessellationCache.delete(key);
            setState((s) =>
              s.data === cached.data
                ? { data: null, isTessellating: false, progress: "", error: null }
                : s,
            );
          }
        })
        .catch(() => {});
    } else {
      setState({ data: null, isTessellating: false, progress: "", error: null });
    }
  }, [aeroplaneId, wingName]);

  const triggerTessellation = useCallback(async () => {
    if (!aeroplaneId || !wingName) return;

    // Cancel any in-flight polling
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const signal = controller.signal;

    setState({ data: null, isTessellating: true, progress: "Starting tessellation…", error: null });

    try {
      const encodedWing = encodeURIComponent(wingName);

      // Get current updated_at for cache validation
      const aeroplaneRes = await fetch(`${API_BASE}/aeroplanes/${aeroplaneId}`, { signal });
      const aeroplane = aeroplaneRes.ok ? await aeroplaneRes.json() : null;
      const updatedAt = aeroplane?.updated_at ?? "";

      // Check cache with current updatedAt
      const key = cacheKey(aeroplaneId, wingName);
      const cached = tessellationCache.get(key);
      if (cached && cached.updatedAt === updatedAt) {
        setState({ data: cached.data, isTessellating: false, progress: "", error: null });
        return;
      }

      // Trigger tessellation
      const postRes = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${encodedWing}/tessellation`,
        { method: "POST", signal },
      );
      if (!postRes.ok) {
        const body = await postRes.text();
        throw new Error(`Tessellation trigger failed: ${postRes.status} ${body}`);
      }

      // Poll for completion
      setState((s) => ({ ...s, progress: "Tessellating geometry…" }));
      const deadline = Date.now() + 120_000;
      while (Date.now() < deadline) {
        if (signal.aborted) return;
        const statusRes = await fetch(`${API_BASE}/aeroplanes/${aeroplaneId}/status?task_type=tessellation`, { signal });
        if (!statusRes.ok) throw new Error(`Status check failed: ${statusRes.status}`);
        const statusData = await statusRes.json();

        if (statusData.status === "SUCCESS") {
          const tessResult = statusData.result;
          if (!tessResult || !tessResult.data) {
            throw new Error("Tessellation result has no data");
          }

          // Store in cache
          tessellationCache.set(key, {
            aeroplaneId,
            wingName,
            updatedAt,
            data: tessResult,
          });

          setState({ data: tessResult, isTessellating: false, progress: "", error: null });
          return;
        }

        if (statusData.status === "FAILURE") {
          throw new Error(statusData.message || "Tessellation failed");
        }

        await new Promise((r) => setTimeout(r, 500));
      }

      throw new Error("Tessellation timed out after 2 minutes");
    } catch (err) {
      console.error("[useTessellation] Error:", err);
      setState({
        data: null,
        isTessellating: false,
        progress: "",
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }, [aeroplaneId, wingName]);

  const clearCache = useCallback(() => {
    if (aeroplaneId && wingName) {
      tessellationCache.delete(cacheKey(aeroplaneId, wingName));
      setState({ data: null, isTessellating: false, progress: "", error: null });
    }
  }, [aeroplaneId, wingName]);

  return { ...state, triggerTessellation, clearCache };
}
