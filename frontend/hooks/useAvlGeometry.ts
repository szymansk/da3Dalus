"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE } from "@/lib/fetcher";

interface AvlGeometryState {
  content: string | null;
  isDirty: boolean;
  isUserEdited: boolean;
  isLoading: boolean;
  error: string | null;
  save: (content: string) => Promise<void>;
  regenerate: () => Promise<string>;
  remove: () => Promise<void>;
  refresh: () => Promise<void>;
}

export function useAvlGeometry(aeroplaneId: string | null): AvlGeometryState {
  const [content, setContent] = useState<string | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [isUserEdited, setIsUserEdited] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchGeometry = useCallback(async () => {
    if (!aeroplaneId) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/avl-geometry`,
      );
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const data = await res.json();
      setContent(data.content);
      setIsDirty(data.is_dirty);
      setIsUserEdited(data.is_user_edited);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }, [aeroplaneId]);

  useEffect(() => {
    fetchGeometry();
  }, [fetchGeometry]);

  const save = useCallback(
    async (newContent: string) => {
      if (!aeroplaneId) return;
      setError(null);
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/avl-geometry`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: newContent }),
        },
      );
      if (!res.ok) throw new Error(`Save failed: ${res.status}`);
      const data = await res.json();
      setContent(data.content);
      setIsDirty(data.is_dirty);
      setIsUserEdited(data.is_user_edited);
    },
    [aeroplaneId],
  );

  const regenerate = useCallback(async () => {
    if (!aeroplaneId) return "";
    setError(null);
    const res = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/avl-geometry/regenerate`,
      { method: "POST" },
    );
    if (!res.ok) throw new Error(`Regenerate failed: ${res.status}`);
    const data = await res.json();
    return data.content as string;
  }, [aeroplaneId]);

  const remove = useCallback(async () => {
    if (!aeroplaneId) return;
    setError(null);
    const res = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/avl-geometry`,
      { method: "DELETE" },
    );
    if (!res.ok && res.status !== 404)
      throw new Error(`Delete failed: ${res.status}`);
    setContent(null);
    setIsDirty(false);
    setIsUserEdited(false);
  }, [aeroplaneId]);

  return {
    content,
    isDirty,
    isUserEdited,
    isLoading,
    error,
    save,
    regenerate,
    remove,
    refresh: fetchGeometry,
  };
}
