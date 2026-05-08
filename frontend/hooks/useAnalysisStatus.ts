"use client";

import { useState, useCallback, useEffect, useMemo } from "react";
import { API_BASE } from "@/lib/fetcher";

export interface AnalysisStatus {
  op_counts: Record<string, number>;
  total_ops: number;
  retrim_active: boolean;
  retrim_debouncing: boolean;
  last_computation: string | null;
}

const EMPTY_STATUS: AnalysisStatus = {
  op_counts: {},
  total_ops: 0,
  retrim_active: false,
  retrim_debouncing: false,
  last_computation: null,
};

const POLL_INTERVAL_ACTIVE = 2000; // 2s while retrim is active

export function useAnalysisStatus(aeroplaneId: string | null) {
  const [status, setStatus] = useState<AnalysisStatus>(EMPTY_STATUS);

  const fetchStatus = useCallback(async () => {
    if (!aeroplaneId) return;
    try {
      const res = await fetch(
        `${API_BASE}/aeroplanes/${encodeURIComponent(aeroplaneId)}/analysis-status`,
      );
      if (!res.ok) return;
      const data: AnalysisStatus = await res.json();
      setStatus(data);
    } catch {
      // Silently ignore — status is advisory
    }
  }, [aeroplaneId]);

  const needsPolling = useMemo(
    () =>
      status.retrim_active ||
      status.retrim_debouncing ||
      (status.op_counts["DIRTY"] ?? 0) > 0 ||
      (status.op_counts["COMPUTING"] ?? 0) > 0,
    [status],
  );

  // Start/stop polling based on active state
  useEffect(() => {
    if (!needsPolling) return;

    const id = setInterval(fetchStatus, POLL_INTERVAL_ACTIVE);
    return () => {
      clearInterval(id);
    };
  }, [needsPolling, fetchStatus]);

  // Fetch on aeroplaneId change; reset when null
  useEffect(() => {
    if (!aeroplaneId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- reset on dep change is intentional
      setStatus(EMPTY_STATUS);
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `${API_BASE}/aeroplanes/${encodeURIComponent(aeroplaneId)}/analysis-status`,
        );
        if (!res.ok || cancelled) return;
        const data: AnalysisStatus = await res.json();
        if (!cancelled) setStatus(data);
      } catch {
        // Silently ignore
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [aeroplaneId]);

  return { status, isPolling: needsPolling, refresh: fetchStatus };
}
