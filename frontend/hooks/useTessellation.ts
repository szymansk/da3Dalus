"use client";

import { useState, useCallback, useEffect, useRef } from "react";
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

/** Fetch the current updated_at timestamp, returning "" on failure. */
async function fetchUpdatedAt(
  aeroplaneId: string,
  signal: AbortSignal,
): Promise<string> {
  const res = await fetch(`${API_BASE}/aeroplanes/${aeroplaneId}`, { signal });
  const aeroplane = res.ok ? await res.json() : null;
  return aeroplane?.updated_at ?? "";
}

/** Return cached data if still valid (matching updatedAt), or null. */
function getCachedIfValid(
  aeroplaneId: string,
  wingName: string,
  updatedAt: string,
): Record<string, unknown> | null {
  const key = cacheKey(aeroplaneId, wingName);
  const cached = tessellationCache.get(key);
  return cached?.updatedAt === updatedAt ? cached.data : null;
}

/** Poll the status endpoint until SUCCESS, FAILURE, or timeout. */
async function pollTessellation(
  aeroplaneId: string,
  encodedWing: string,
  signal: AbortSignal,
): Promise<Record<string, unknown>> {
  const deadline = Date.now() + 120_000;
  while (Date.now() < deadline) {
    if (signal.aborted) throw new Error("Aborted");
    const statusRes = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/status?task_type=tessellation&wing_name=${encodedWing}`,
      { signal },
    );
    if (!statusRes.ok) throw new Error(`Status check failed: ${statusRes.status}`);
    const statusData = await statusRes.json();

    if (statusData.status === "SUCCESS") {
      const tessResult = statusData.result;
      if (!tessResult || !tessResult.data) {
        throw new Error("Tessellation result has no data");
      }
      return tessResult;
    }
    if (statusData.status === "FAILURE") {
      throw new Error(statusData.message || "Tessellation failed");
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("Tessellation timed out after 2 minutes");
}

/** Run the full tessellation workflow: cache check, trigger, poll, store. */
async function executeTessellation(
  aeroplaneId: string,
  wingName: string,
  signal: AbortSignal,
  onProgress: (progress: string) => void,
): Promise<Record<string, unknown> | null> {
  const encodedWing = encodeURIComponent(wingName);
  const updatedAt = await fetchUpdatedAt(aeroplaneId, signal);

  const cachedData = getCachedIfValid(aeroplaneId, wingName, updatedAt);
  if (cachedData) return cachedData;

  // Trigger tessellation
  const postRes = await fetch(
    `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${encodedWing}/tessellation`,
    { method: "POST", signal },
  );
  if (!postRes.ok) {
    const body = await postRes.text();
    throw new Error(`Tessellation trigger failed: ${postRes.status} ${body}`);
  }

  onProgress("Tessellating geometry…");
  const tessResult = await pollTessellation(aeroplaneId, encodedWing, signal);

  // Store in cache
  const key = cacheKey(aeroplaneId, wingName);
  tessellationCache.set(key, { aeroplaneId, wingName, updatedAt, data: tessResult });

  return tessResult;
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
    const emptyState: TessellationState = {
      data: null, isTessellating: false, progress: "", error: null,
    };

    if (!aeroplaneId || !wingName) {
      lastKeyRef.current = "";
      // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional reset on prop change
      setState(emptyState);
      return;
    }

    const key = cacheKey(aeroplaneId, wingName);
    if (key === lastKeyRef.current && state.data) return; // same wing, already showing
    lastKeyRef.current = key;

    const cached = tessellationCache.get(key);
    if (!cached) {
      setState(emptyState);
      return;
    }

    // Show cached data optimistically
    setState({ data: cached.data, isTessellating: false, progress: "", error: null });

    // Validate in background — if aeroplane updated_at changed, invalidate
    fetch(`${API_BASE}/aeroplanes/${aeroplaneId}`)
      .then((r) => r.json())
      .then((aeroplane) => {
        if (aeroplane.updated_at !== cached.updatedAt) {
          tessellationCache.delete(key);
          setState((s) =>
            s.data === cached.data ? emptyState : s,
          );
        }
      })
      .catch(() => {});
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
      const result = await executeTessellation(
        aeroplaneId, wingName, signal,
        (progress) => setState((s) => ({ ...s, progress })),
      );
      if (result) {
        setState({ data: result, isTessellating: false, progress: "", error: null });
      }
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
