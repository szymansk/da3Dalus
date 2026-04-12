"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import type { ReactNode } from "react";

export type TreeMode = "wingconfig" | "asb";

interface AeroplaneContextValue {
  aeroplaneId: string | null;
  selectedWing: string | null;
  selectedXsecIndex: number | null;
  treeMode: TreeMode;
  setAeroplaneId: (id: string | null) => void;
  selectWing: (name: string | null) => void;
  selectXsec: (index: number | null) => void;
  setTreeMode: (mode: TreeMode) => void;
}

const Ctx = createContext<AeroplaneContextValue | null>(null);

const STORAGE_KEY = "da3dalus_aeroplane_id";

export function AeroplaneProvider({ children }: { children: ReactNode }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // Start with null on both server and client to avoid hydration mismatch.
  // Restore from URL/localStorage in useEffect (client-only).
  const [aeroplaneId, setAeroplaneIdRaw] = useState<string | null>(null);
  const [selectedWing, setSelectedWing] = useState<string | null>(null);
  const [selectedXsecIndex, setSelectedXsecIndex] = useState<number | null>(
    null,
  );
  const [treeMode, setTreeMode] = useState<TreeMode>("wingconfig");

  const setAeroplaneId = useCallback(
    (id: string | null) => {
      setAeroplaneIdRaw(id);
      if (id) {
        localStorage.setItem(STORAGE_KEY, id);
        // Update URL search param without full navigation
        const params = new URLSearchParams(searchParams.toString());
        params.set("id", id);
        router.replace(`${pathname}?${params.toString()}`);
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    },
    [searchParams, router, pathname],
  );

  // Restore aeroplaneId from URL or localStorage on mount (client-only)
  useEffect(() => {
    const urlId = searchParams.get("id");
    const storedId = localStorage.getItem(STORAGE_KEY);
    const resolved = urlId ?? storedId ?? null;
    if (resolved && resolved !== aeroplaneId) {
      setAeroplaneIdRaw(resolved);
      if (resolved) localStorage.setItem(STORAGE_KEY, resolved);
    }
  }, [searchParams, aeroplaneId]);

  const selectWing = useCallback((name: string | null) => {
    setSelectedWing(name);
    setSelectedXsecIndex(null);
  }, []);

  const selectXsec = useCallback((index: number | null) => {
    setSelectedXsecIndex(index);
  }, []);

  return (
    <Ctx
      value={{
        aeroplaneId,
        selectedWing,
        selectedXsecIndex,
        treeMode,
        setAeroplaneId,
        selectWing,
        selectXsec,
        setTreeMode,
      }}
    >
      {children}
    </Ctx>
  );
}

export function useAeroplaneContext(): AeroplaneContextValue {
  const ctx = useContext(Ctx);
  if (!ctx)
    throw new Error(
      "useAeroplaneContext must be used within AeroplaneProvider",
    );
  return ctx;
}
