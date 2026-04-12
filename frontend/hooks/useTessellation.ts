"use client";

import { useState, useCallback } from "react";
import { API_BASE } from "@/lib/fetcher";

interface TessellationState {
  data: Record<string, unknown> | null;
  isTessellating: boolean;
  progress: string;
  error: string | null;
}

export function useTessellation(aeroplaneId: string | null, wingName: string | null) {
  const [state, setState] = useState<TessellationState>({
    data: null,
    isTessellating: false,
    progress: "",
    error: null,
  });

  const triggerTessellation = useCallback(async () => {
    if (!aeroplaneId || !wingName) return;

    setState({ data: null, isTessellating: true, progress: "Starting tessellation…", error: null });

    try {
      const encodedWing = encodeURIComponent(wingName);

      // 1. Trigger the tessellation task
      const postRes = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${encodedWing}/tessellation`,
        { method: "POST" },
      );
      if (!postRes.ok) {
        const body = await postRes.text();
        throw new Error(`Tessellation trigger failed: ${postRes.status} ${body}`);
      }

      // 2. Poll for completion
      setState((s) => ({ ...s, progress: "Tessellating geometry…" }));
      const deadline = Date.now() + 120_000;
      while (Date.now() < deadline) {
        const statusRes = await fetch(`${API_BASE}/aeroplanes/${aeroplaneId}/status`);
        if (!statusRes.ok) throw new Error(`Status check failed: ${statusRes.status}`);
        const statusData = await statusRes.json();

        if (statusData.status === "SUCCESS") {
          // The result contains the three-cad-viewer JSON directly
          const tessResult = statusData.result;
          if (!tessResult || !tessResult.data) {
            throw new Error("Tessellation result has no data");
          }

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

  return { ...state, triggerTessellation };
}
