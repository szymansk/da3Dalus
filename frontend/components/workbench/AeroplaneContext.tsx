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

interface AeroplaneContextValue {
  aeroplaneId: string | null;
  selectedWing: string | null;
  selectedXsecIndex: number | null;
  setAeroplaneId: (id: string | null) => void;
  selectWing: (name: string | null) => void;
  selectXsec: (index: number | null) => void;
}

const Ctx = createContext<AeroplaneContextValue | null>(null);

const STORAGE_KEY = "da3dalus_aeroplane_id";

export function AeroplaneProvider({ children }: { children: ReactNode }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // Initialize from URL param > localStorage > null
  const [aeroplaneId, setAeroplaneIdRaw] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    return (
      searchParams.get("id") ??
      localStorage.getItem(STORAGE_KEY) ??
      null
    );
  });
  const [selectedWing, setSelectedWing] = useState<string | null>(null);
  const [selectedXsecIndex, setSelectedXsecIndex] = useState<number | null>(
    null,
  );

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

  // Sync from URL on mount / URL change
  useEffect(() => {
    const urlId = searchParams.get("id");
    if (urlId && urlId !== aeroplaneId) {
      setAeroplaneIdRaw(urlId);
      localStorage.setItem(STORAGE_KEY, urlId);
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
        setAeroplaneId,
        selectWing,
        selectXsec,
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
